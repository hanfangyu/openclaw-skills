import os
import sys
import json
import subprocess
from difflib import SequenceMatcher

SKILLS_DIR = "/root/.openclaw/workspace/skills"
SIMILARITY_THRESHOLD = 0.7

def get_local_skills():
    skills = []
    for root, dirs, files in os.walk(SKILLS_DIR):
        if "SKILL.md" in files:
            skill_path = root
            skill_name = os.path.basename(root)
            skill_desc = ""
            with open(os.path.join(root, "SKILL.md"), "r", encoding="utf-8") as f:
                content = f.read()
                # 提取description
                if "description:" in content:
                    desc_line = [l for l in content.split("\n") if "description:" in l][0]
                    skill_desc = desc_line.split("description:", 1)[1].strip().strip('"')
            skills.append({
                "name": skill_name,
                "description": skill_desc,
                "path": skill_path
            })
    return skills

def calculate_similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def search_local_skills(query):
    skills = get_local_skills()
    matches = []
    for skill in skills:
        name_sim = calculate_similarity(query, skill["name"])
        desc_sim = calculate_similarity(query, skill["description"])
        max_sim = max(name_sim, desc_sim)
        if max_sim >= 0.4:
            matches.append({
                **skill,
                "similarity": max_sim
            })
    matches.sort(key=lambda x: x["similarity"], reverse=True)
    return matches

def search_online_skills(query):
    try:
        result = subprocess.run(
            ["clawhub", "search", query],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return []
        lines = [l.strip() for l in result.stdout.split("\n") if l.strip() and not l.startswith("- Searching")]
        skills = []
        for line in lines:
            parts = line.split("  ")
            parts = [p for p in parts if p]
            if len(parts) >= 2:
                name = parts[0].strip()
                desc = parts[1].strip()
                skills.append({
                    "name": name,
                    "description": desc,
                    "similarity": 0.6
                })
        return skills
    except Exception as e:
        print(f"在线搜索失败：{e}")
        return []

def install_skill(skill_name):
    try:
        result = subprocess.run(
            ["clawhub", "install", skill_name, "--dir", SKILLS_DIR],
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

def main():
    if len(sys.argv) < 2:
        print("使用方法：python3 matcher.py <任务关键词>")
        return
    
    query = sys.argv[1]
    print(f"🔍 正在为任务「{query}」匹配技能...")
    
    # 搜索本地技能
    local_matches = search_local_skills(query)
    if local_matches and local_matches[0]["similarity"] >= SIMILARITY_THRESHOLD:
        best = local_matches[0]
        print(f"✅ 本地匹配到最优技能：{best['name']}")
        print(f"   描述：{best['description']}")
        print(f"   匹配度：{int(best['similarity']*100)}%")
        print(f"   路径：{best['path']}")
        return
    
    if local_matches:
        print("ℹ️ 本地找到以下相关技能（匹配度不足自动安装阈值）：")
        for i, skill in enumerate(local_matches[:3]):
            print(f"{i+1}. {skill['name']} - {skill['description']}（{int(skill['similarity']*100)}%）")
    
    # 搜索在线技能
    print("\n🌐 正在搜索在线可用技能...")
    online_matches = search_online_skills(query)
    if not online_matches:
        print("❌ 未找到任何相关技能，建议手动编写自定义技能")
        return
    
    print("✅ 在线找到以下相关技能：")
    for i, skill in enumerate(online_matches[:5]):
        print(f"{i+1}. {skill['name']} - {skill['description']}")
    
    # 自动安装第一个
    if len(sys.argv) >=3 and sys.argv[2] == "--auto-install":
        best_online = online_matches[0]
        print(f"\n🚀 自动安装最优技能：{best_online['name']}")
        success, log = install_skill(best_online['name'])
        if success:
            print(f"✅ 技能安装成功！")
        else:
            print(f"❌ 安装失败：{log}")

if __name__ == "__main__":
    main()
