"""Skills API：读取本地 SKILL.md 与脚本信息，用于前端展示。"""

from pathlib import Path
from fastapi import APIRouter

skills_router = APIRouter(prefix="/api/skills", tags=["Skills"])


@skills_router.get("")
async def list_skills():
    base = Path("skills")
    if not base.exists():
        return {"skills": []}

    skills = []
    for skill_dir in sorted([x for x in base.iterdir() if x.is_dir()]):
        skill_md = skill_dir / "SKILL.md"
        script_dir = skill_dir / "scripts"
        scripts = []
        if script_dir.exists():
            scripts = sorted([f.name for f in script_dir.glob("*.py")])

        desc = ""
        if skill_md.exists():
            text = skill_md.read_text(encoding="utf-8")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            desc = lines[1] if len(lines) > 1 else (lines[0] if lines else "")

        skills.append(
            {
                "name": skill_dir.name,
                "has_skill_md": skill_md.exists(),
                "scripts": scripts,
                "description": desc,
            }
        )

    return {"skills": skills}
