from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class BOMItem:
    material: str
    quantity: float
    level: int


@dataclass
class BOMNode:
    material: str
    qty_per_parent: float


class BOMService:
    def __init__(self) -> None:
        self._bom: Dict[str, List[BOMNode]] = {}

    def add_relation(self, parent: str, child: str, quantity: float) -> None:
        if parent not in self._bom:
            self._bom[parent] = []
        self._bom[parent].append(BOMNode(material=child, qty_per_parent=quantity))

    def load_relations(self, relations: List[Tuple[str, str, float]]) -> None:
        for parent, child, qty in relations:
            self.add_relation(parent, child, qty)

    def explode(self, parent: str) -> List[BOMItem]:
        visited: set = set()
        result: List[BOMItem] = []
        self._explode_recursive(parent, 1.0, 0, visited, result)
        return result

    def _explode_recursive(
        self,
        material: str,
        parent_qty: float,
        level: int,
        visited: set,
        result: List[BOMItem],
    ) -> None:
        if material in visited:
            return
        visited.add(material)

        children = self._bom.get(material, [])
        for node in children:
            if node.material in visited:
                continue
            total_qty = parent_qty * node.qty_per_parent
            result.append(
                BOMItem(material=node.material, quantity=total_qty, level=level + 1)
            )
            self._explode_recursive(node.material, total_qty, level + 1, visited, result)

        visited.discard(material)

    def flatten(self, parent: str) -> List[Tuple[str, float]]:
        items = self.explode(parent)
        aggregated: Dict[str, float] = defaultdict(float)
        for item in items:
            aggregated[item.material] += item.quantity
        return sorted(aggregated.items())


def build_sample_bom() -> BOMService:
    svc = BOMService()
    svc.load_relations(
        [
            ("自行车", "车架", 1),
            ("自行车", "车轮", 2),
            ("自行车", "把手", 1),
            ("车轮", "轮胎", 1),
            ("车轮", "轮毂", 1),
            ("轮毂", "辐条", 12),
            ("车架", "前叉", 1),
        ]
    )
    return svc


def main() -> None:
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="BOM 展开服务")
    parser.add_argument("parent", help="父物料编码")
    parser.add_argument("--relations", help="BOM 关系 JSON 文件路径")
    parser.add_argument("--format", choices=["tree", "flat", "json"], default="flat", help="输出格式")
    args = parser.parse_args()

    svc = BOMService()

    if args.relations:
        with open(args.relations, encoding="utf-8") as f:
            data = json.load(f)
        svc.load_relations([(r["parent"], r["child"], r["quantity"]) for r in data])
    else:
        svc = build_sample_bom()

    if args.format == "json":
        items = svc.explode(args.parent)
        output = [
            {"material": i.material, "quantity": i.quantity, "level": i.level}
            for i in items
        ]
        print(json.dumps(output, ensure_ascii=False, indent=2))
    elif args.format == "tree":
        items = svc.explode(args.parent)
        print(f"{args.parent}")
        for item in items:
            indent = "  " * item.level
            print(f"{indent}├─ {item.material} × {item.quantity:g}")
    else:
        flat = svc.flatten(args.parent)
        print(f"{'物料':<12}{'用量':>10}")
        print("-" * 22)
        for mat, qty in flat:
            print(f"{mat:<12}{qty:>10g}")


if __name__ == "__main__":
    main()
