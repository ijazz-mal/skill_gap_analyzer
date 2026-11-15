import json

def load_roles():
    with open("data/roles.json") as f:
        return json.load(f)

def compute_gaps(role, my_skills):
    roles = load_roles()
    required = roles[role]
    gaps = []
    for item in required:
        if item["skill"] not in my_skills:
            gaps.append(item)
    gaps.sort(key=lambda g: g["demand"], reverse = True)
    return gaps

if __name__ == "__main__":
    result = compute_gaps("Data Analyst", ["Excel", "Communication"])
    for g in result:
        print(g["skill"], g["demand"])
