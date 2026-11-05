"""
NewsOps - Dependency Impact Scan Endpoint.

Implements:
  POST /impact/scan  — scan a requirements.txt or package.json for advisories
  PUT  /me/project   — save the user's project file for re-scanning
"""

import re
import json as _json
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from ..core.logging import logger
from ..db.mongodb import get_db
from ..models.user import User
from .deps import get_current_user

router = APIRouter(tags=["Impact"])

# ---------------------------------------------------------------------------
# Sample advisory database (offline / demo mode)
# ---------------------------------------------------------------------------
SAMPLE_ADVISORIES = [
    {
        "package": "requests",
        "ecosystem": "pypi",
        "severity": "HIGH",
        "advisory_id": "GHSA-j8r2-6x86-q33q",
        "summary": "Proxy-Authorization header leak on redirects",
        "fix": "pip install 'requests>=2.31.0'",
        "affected_range": "<2.31.0",
    },
    {
        "package": "pillow",
        "ecosystem": "pypi",
        "severity": "HIGH",
        "advisory_id": "GHSA-44wm-f244-xhp3",
        "summary": "Buffer overflow in TIFF image parsing",
        "fix": "pip install 'Pillow>=10.0.1'",
        "affected_range": "<10.0.1",
    },
    {
        "package": "lodash",
        "ecosystem": "npm",
        "severity": "HIGH",
        "advisory_id": "GHSA-p6mc-m468-83gw",
        "summary": "Prototype pollution via zipObjectDeep",
        "fix": "npm install lodash@^4.17.21",
        "affected_range": "<4.17.21",
    },
    {
        "package": "axios",
        "ecosystem": "npm",
        "severity": "MODERATE",
        "advisory_id": "GHSA-42xw-2xvc-qx8m",
        "summary": "Server-side request forgery via open redirect",
        "fix": "npm install axios@^1.6.0",
        "affected_range": "<1.6.0",
    },
    {
        "package": "numpy",
        "ecosystem": "pypi",
        "severity": "LOW",
        "advisory_id": "GHSA-fpfv-jqm9-f5jm",
        "summary": "Array stride-based buffer overflow",
        "fix": "pip install 'numpy>=1.24.4'",
        "affected_range": "<1.24.4",
    },
    {
        "package": "express",
        "ecosystem": "npm",
        "severity": "MODERATE",
        "advisory_id": "GHSA-rv95-896h-c2vc",
        "summary": "Open redirect in res.location()",
        "fix": "npm install express@^4.19.2",
        "affected_range": "<4.19.2",
    },
]

ADVISORY_INDEX = {a["package"].lower(): a for a in SAMPLE_ADVISORIES}


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _detect_ecosystem(content: str) -> Literal["pypi", "npm"]:
    stripped = content.strip()
    if stripped.startswith("{"):
        return "npm"
    return "pypi"


def _parse_requirements_txt(content: str) -> list[str]:
    packages = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip version specifiers: requests>=2.0, pillow==9.0
        name = re.split(r"[>=<!;\[\s]", line)[0].strip().lower()
        if name:
            packages.append(name)
    return packages


def _parse_package_json(content: str) -> list[str]:
    try:
        data = _json.loads(content)
    except _json.JSONDecodeError:
        return []
    deps = {}
    deps.update(data.get("dependencies", {}))
    deps.update(data.get("devDependencies", {}))
    return [k.lower() for k in deps]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    content: str  # raw text of requirements.txt or package.json


class AdvisoryRow(BaseModel):
    package: str
    status: Literal["affected", "possible", "clear"]
    advisory_id: Optional[str] = None
    severity: Optional[str] = None
    summary: Optional[str] = None
    fix: Optional[str] = None
    source: str = "osv"


class ScanResponse(BaseModel):
    ecosystem: str
    total: int
    affected: int
    possible: int
    clear: int
    items: list[AdvisoryRow]
    source: str = "osv"


class ProjectSaveRequest(BaseModel):
    content: str
    filename: Optional[str] = "requirements.txt"


# ---------------------------------------------------------------------------
# POST /impact/scan
# ---------------------------------------------------------------------------
@router.post(
    "/impact/scan",
    response_model=ScanResponse,
    summary="Scan requirements.txt or package.json for known advisories",
)
async def scan_impact(payload: ScanRequest):
    if not payload.content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Content is empty.",
        )

    ecosystem = _detect_ecosystem(payload.content)

    if ecosystem == "npm":
        packages = _parse_package_json(payload.content)
    else:
        packages = _parse_requirements_txt(payload.content)

    if not packages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No packages found in the submitted content.",
        )

    rows: list[AdvisoryRow] = []
    affected_count = 0
    possible_count = 0
    clear_count = 0

    for pkg in packages:
        adv = ADVISORY_INDEX.get(pkg)
        if adv and adv["ecosystem"] == ecosystem:
            rows.append(AdvisoryRow(
                package=pkg,
                status="affected",
                advisory_id=adv["advisory_id"],
                severity=adv["severity"],
                summary=adv["summary"],
                fix=adv["fix"],
                source="sample",
            ))
            affected_count += 1
        elif pkg in ("urllib3", "certifi", "charset-normalizer", "react", "react-dom"):
            rows.append(AdvisoryRow(
                package=pkg,
                status="possible",
                summary="Check upstream for recent advisories",
                source="sample",
            ))
            possible_count += 1
        else:
            rows.append(AdvisoryRow(package=pkg, status="clear", source="sample"))
            clear_count += 1

    logger.info(f"Impact scan: {len(packages)} packages, {affected_count} affected, ecosystem={ecosystem}")

    return ScanResponse(
        ecosystem=ecosystem,
        total=len(packages),
        affected=affected_count,
        possible=possible_count,
        clear=clear_count,
        items=rows,
        source="sample",
    )


# ---------------------------------------------------------------------------
# PUT /me/project  (save user's project file)
# ---------------------------------------------------------------------------
@router.put(
    "/me/project",
    summary="Save the current user's project dependency file",
)
async def save_project(
    payload: ProjectSaveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    await db.users.update_one(
        {"_id": current_user.id},
        {"$set": {
            "project_file": payload.content,
            "project_filename": payload.filename,
        }},
    )
    return {"saved": True, "filename": payload.filename, "user": current_user.chat_handle}
