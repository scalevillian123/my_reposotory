import argparse
from pathlib import Path

import pandas as pd

ENDING = {"fulfilled": "Заявка выполнена", "rejected": "Заявка отклонена", "cancelled": "Заявка отменена"}


def load(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    return df.sort_values(["ProcessInstanceId", "EventIndex"]).reset_index(drop=True)


def routes(df):
    records = []
    for pid, g in df.groupby("ProcessInstanceId"):
        seq = ["Регистрация заявки"]
        seq += list(g[g.EventType == "task_completed"].ActivityName)
        end = g[g.EventType == "process_completed"].iloc[0].Result
        seq.append(ENDING[end])
        records.append({"pid": pid, "route": " > ".join(seq)})
    return pd.DataFrame(records)


def main():
    parser = argparse.ArgumentParser(description="Восстановление процесса по журналу событий")
    parser.add_argument("--input", default="students.csv")
    parser.add_argument("--variants", default="variants.csv")
    parser.add_argument("--transitions", default="student_transitions.csv")
    args = parser.parse_args()

    df = load(args.input)
    R = routes(df)

    counts = R.route.value_counts()
    variants = pd.DataFrame({
        "Variant": [chr(65 + i) for i in range(len(counts))],
        "Route": counts.index,
        "NumberOfCases": counts.values,
        "Share": (counts.values / len(R)).round(3),
    })
    variants.to_csv(args.variants, index=False, encoding="utf-8")

    pairs = {}
    for route in R.route:
        parts = route.split(" > ")
        for a, b in zip(parts, parts[1:]):
            pairs[(a, b)] = pairs.get((a, b), 0) + 1
    trans = pd.DataFrame(
        [{"SourceActivity": a, "TargetActivity": b} for a, b in pairs],
        columns=["SourceActivity", "TargetActivity"],
    )
    trans.to_csv(args.transitions, index=False, encoding="utf-8")

    total = df.ProcessInstanceId.nunique()
    print(f"событий: {len(df)}, экземпляров: {total}")
    print(df[df.EventType == "process_completed"].Result.value_counts().to_string())
    print(f"маршрутов: {len(counts)}, покрытие вариантов: {variants.Share.sum():.3f}")
    print(variants[["Variant", "NumberOfCases", "Share"]].to_string(index=False))
    print(f"переходов: {len(trans)}")
    print(f"записано: {Path(args.variants).resolve()}, {Path(args.transitions).resolve()}")


if __name__ == "__main__":
    main()
