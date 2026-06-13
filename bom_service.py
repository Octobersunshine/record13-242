from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


class BOMCircularReferenceError(Exception):
    def __init__(self, path: List[str]) -> None:
        self.path = path
        cycle = " → ".join(path + [path[0]])
        super().__init__(f"BOM 检测到循环引用: {cycle}")


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
        path: List[str] = []
        result: List[BOMItem] = []
        self._explode_recursive(parent, 1.0, 0, visited, path, result)
        return result

    def _explode_recursive(
        self,
        material: str,
        parent_qty: float,
        level: int,
        visited: set,
        path: List[str],
        result: List[BOMItem],
    ) -> None:
        if material in visited:
            return
        visited.add(material)
        path.append(material)

        children = self._bom.get(material, [])
        for node in children:
            if node.material in visited:
                raise BOMCircularReferenceError(path + [node.material])
            total_qty = parent_qty * node.qty_per_parent
            result.append(
                BOMItem(material=node.material, quantity=total_qty, level=level + 1)
            )
            self._explode_recursive(node.material, total_qty, level + 1, visited, path, result)

        path.pop()
        visited.discard(material)

    def flatten(self, parent: str) -> List[Tuple[str, float]]:
        items = self.explode(parent)
        aggregated: Dict[str, float] = defaultdict(float)
        for item in items:
            aggregated[item.material] += item.quantity
        return sorted(aggregated.items())

    def get_low_level_codes(self, parent: str) -> Dict[str, int]:
        llc: Dict[str, int] = {parent: 0}
        visited: set = set()
        path: List[str] = []
        self._llc_recursive(parent, 0, visited, path, llc)
        return llc

    def _llc_recursive(
        self,
        material: str,
        current_level: int,
        visited: set,
        path: List[str],
        llc: Dict[str, int],
    ) -> None:
        if material in visited:
            return
        visited.add(material)
        path.append(material)

        children = self._bom.get(material, [])
        for node in children:
            if node.material in visited:
                raise BOMCircularReferenceError(path + [node.material])
            child_level = current_level + 1
            if node.material not in llc or child_level > llc[node.material]:
                llc[node.material] = child_level
            self._llc_recursive(node.material, child_level, visited, path, llc)

        path.pop()
        visited.discard(material)

    def compute_global_low_level_codes(self) -> Dict[str, int]:
        all_materials: set = set()
        for parent, children in self._bom.items():
            all_materials.add(parent)
            for child in children:
                all_materials.add(child.material)

        child_materials: set = set()
        for children in self._bom.values():
            for child in children:
                child_materials.add(child.material)
        roots = all_materials - child_materials

        global_llc: Dict[str, int] = {}
        for root in sorted(roots):
            root_llc = self.get_low_level_codes(root)
            for mat, code in root_llc.items():
                if mat not in global_llc or code > global_llc[mat]:
                    global_llc[mat] = code
        return global_llc


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
    parser.add_argument("--format", choices=["tree", "flat", "json", "llc", "llc-global"], default="flat", help="输出格式")
    args = parser.parse_args()

    svc = BOMService()

    if args.relations:
        with open(args.relations, encoding="utf-8") as f:
            data = json.load(f)
        svc.load_relations([(r["parent"], r["child"], r["quantity"]) for r in data])
    else:
        svc = build_sample_bom()

    try:
        if args.format == "json":
            items = svc.explode(args.parent)
            llc = svc.get_low_level_codes(args.parent)
            output = [
                {"material": i.material, "quantity": i.quantity, "level": i.level, "low_level_code": llc[i.material]}
                for i in items
            ]
            print(json.dumps(output, ensure_ascii=False, indent=2))
        elif args.format == "tree":
            items = svc.explode(args.parent)
            llc = svc.get_low_level_codes(args.parent)
            print(f"{args.parent} (LLC={llc[args.parent]})")
            for item in items:
                indent = "  " * item.level
                print(f"{indent}├─ {item.material} × {item.quantity:g} (LLC={llc[item.material]})")
        elif args.format == "llc":
            llc = svc.get_low_level_codes(args.parent)
            print(f"{'物料':<12}{'低层码':>8}")
            print("-" * 20)
            for mat, code in sorted(llc.items(), key=lambda x: (x[1], x[0])):
                print(f"{mat:<12}{code:>8}")
        elif args.format == "llc-global":
            llc = svc.compute_global_low_level_codes()
            print(f"{'物料':<12}{'低层码':>8}")
            print("-" * 20)
            for mat, code in sorted(llc.items(), key=lambda x: (x[1], x[0])):
                print(f"{mat:<12}{code:>8}")
        else:
            flat = svc.flatten(args.parent)
            llc = svc.get_low_level_codes(args.parent)
            print(f"{'物料':<12}{'用量':>10}{'低层码':>8}")
            print("-" * 30)
            for mat, qty in flat:
                print(f"{mat:<12}{qty:>10g}{llc[mat]:>8}")
    except BOMCircularReferenceError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
