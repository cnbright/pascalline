#!/usr/bin/env python3
"""按用户输入价格比较含盖/去盖的线性条件估价；不是嘉立创实时报价。

仅使用现有 STL 实体体积，密度默认值是假设，不是材料规格保证。
每种材料先按总克重乘单价，再分别与用户给定的该组费用下限取较大值。
这个下限只是用户输入的估算条件，不代表嘉立创按材料组收最低费；
平台实际最低收费可能按每文件或每件计算，应以实际报价规则为准。
运费、税费、其它附加费均为固定金额，两种方案采用相同输入。
不处理按文件最低收费、支撑重量、价格阶梯或工艺附加费规则；这些
只能按实际报价自行调整。未包含尚未实施的设计修改、重新导出件、
返工、五金和实物测试成本；不证明现有零件已通过厂家可制造性审核。
"""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path


MATERIALS = ("9600", "3201PA-F")
ZERO = Decimal("0")


def nonnegative(value: str) -> Decimal:
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("请输入有效数字") from exc
    if not number.is_finite() or number < ZERO:
        raise argparse.ArgumentTypeError("数字必须有限且不小于零")
    return number


def positive(value: str) -> Decimal:
    number = nonnegative(value)
    if number == ZERO:
        raise argparse.ArgumentTypeError("密度必须大于零")
    return number


def read_parts(path: Path) -> list[dict]:
    parts = []
    seen = set()
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if row["row_type"] != "part":
                continue  # CSV subtotal/total rows are for inspection, not summation.
            name = row["part"]
            if name in seen:
                raise ValueError(f"重复零件: {name}")
            seen.add(name)
            quantity = int(row["quantity"])
            volume = positive(row["unit_volume_cm3"])
            if quantity <= 0 or row["material"] not in MATERIALS:
                raise ValueError(f"无效数量或材料: {name}")
            total = volume * quantity
            if total != nonnegative(row["total_volume_cm3"]):
                raise ValueError(f"零件体积小计与单件×数量不一致: {name}")
            parts.append({"name": name, "material": row["material"],
                          "quantity": quantity, "volume": total})
    if not parts or "top_cover" not in seen:
        raise ValueError("成本基数必须含零件行和 top_cover，才能比较含盖/去盖")
    return parts


def estimate(parts: list[dict], include_cover: bool,
             rates: dict, densities: dict, minimums: dict,
             extras: Decimal) -> dict:
    selected = [p for p in parts if include_cover or p["name"] != "top_cover"]
    materials = {}
    for material in MATERIALS:
        volume = sum((p["volume"] for p in selected if p["material"] == material), ZERO)
        mass = volume * densities[material]
        linear = mass * rates[material]
        charge = max(linear, minimums[material]) if volume else ZERO
        materials[material] = {"volume_cm3": volume, "mass_g": mass,
                               "linear_charge": linear, "charge": charge}
    return {"parts": sum(p["quantity"] for p in selected), "materials": materials,
            "extras": extras,
            "total": sum((m["charge"] for m in materials.values()), ZERO) + extras}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--basis", type=Path,
                        default=Path(__file__).with_name("parts_cost_basis.csv"))
    parser.add_argument("--resin-price-per-g", required=True, type=nonnegative,
                        help="9600 每克价格，单位元/g；由用户提供")
    parser.add_argument("--nylon-price-per-g", required=True, type=nonnegative,
                        help="3201PA-F 每克价格，单位元/g；由用户提供")
    parser.add_argument("--resin-density", type=positive, default=Decimal("1.10"),
                        help="9600 假设密度，g/cm³；默认1.10")
    parser.add_argument("--nylon-density", type=positive, default=Decimal("1.00"),
                        help="3201PA-F 假设密度，g/cm³；默认1.00")
    parser.add_argument("--resin-minimum", type=nonnegative, default=ZERO,
                        help="用户给定树脂组费用下限，元；非平台规则；默认0")
    parser.add_argument("--nylon-minimum", type=nonnegative, default=ZERO,
                        help="用户给定尼龙组费用下限，元；非平台规则；默认0")
    parser.add_argument("--shipping", type=nonnegative, default=ZERO,
                        help="两种材料合计运费，元；默认0")
    parser.add_argument("--taxes", type=nonnegative, default=ZERO,
                        help="另加税费固定金额，元；默认0，已含税单价勿重复加")
    parser.add_argument("--surcharge", type=nonnegative, default=ZERO,
                        help="其它固定附加费，元；默认0")
    args = parser.parse_args(argv)
    try:
        parts = read_parts(args.basis)
    except (OSError, KeyError, ValueError, argparse.ArgumentTypeError) as exc:
        parser.error(f"无法读取成本基数: {exc}")
    rates = dict(zip(MATERIALS, (args.resin_price_per_g, args.nylon_price_per_g)))
    densities = dict(zip(MATERIALS, (args.resin_density, args.nylon_density)))
    minimums = dict(zip(MATERIALS, (args.resin_minimum, args.nylon_minimum)))
    extras = args.shipping + args.taxes + args.surcharge
    print("线性条件估算；不是嘉立创实时报价，也不是厂家可制造性确认。")
    print(f"成本基数: {args.basis.resolve()}")
    print("公式: Σ max(材料体积 × 假设密度 × 每克单价, 用户输入的该组费用下限) + 附加费")
    print("该组下限是假设条件，不代表平台按材料组收费；实际最低费可能按每文件或每件计算。")
    for material in MATERIALS:
        print(f"{material}: 单价 {rates[material]} 元/g；假设密度 {densities[material]} g/cm³；"
              f"用户给定该组费用下限 {minimums[material]} 元")
    print(f"固定附加: 运费 {args.shipping} + 税费 {args.taxes} + 其它 {args.surcharge} = {extras} 元")
    results = []
    for include_cover, label in ((True, "含盖"), (False, "去盖")):
        result = estimate(parts, include_cover, rates, densities, minimums, extras)
        results.append(result)
        print(f"\n{label}：{result['parts']} 件")
        for material, detail in result["materials"].items():
            print(f"  {material}: {detail['volume_cm3']:.3f} cm³ / {detail['mass_g']:.3f} g；"
                  f"按克 {detail['linear_charge']:.2f} 元；应用输入下限 {detail['charge']:.2f} 元")
        print(f"  条件估算合计: {result['total']:.2f} 元")
    print(f"\n同一组输入条件下，去盖减少: {results[0]['total'] - results[1]['total']:.2f} 元")
    print("未计入未实施的设计修改、返工、五金和测试成本；未模拟按文件收费、支撑或价格阶梯。")
    print("费用下限和附加费默认0仅表示未加入估算，不代表厂家免费或无最低收费。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
