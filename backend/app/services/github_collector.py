from datetime import datetime, timezone
from typing import Any, Dict, List
import httpx

class GitHubAuditCollector:
    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.base_url = base_url

    async def get_branch_protection(self, org: str, repo: str, branch: str = "main") -> Dict[str, Any]:
        """Ingests CC8.1 branch protection rules (approvals, admin bypass, status checks)."""
        url = f"{self.base_url}/repos/{org}/{repo}/branches/{branch}/protection"
        async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                return {"branch_protected": False, "reason": "No protection rule configured"}
            resp.raise_for_status()
            data = resp.json()

            return {
                "branch_protected": True,
                "required_approving_review_count": data.get("required_pull_request_reviews", {}).get("required_approving_review_count", 0),
                "dismiss_stale_reviews": data.get("required_pull_request_reviews", {}).get("dismiss_stale_reviews", False),
                "require_code_owner_reviews": data.get("required_pull_request_reviews", {}).get("require_code_owner_reviews", False),
                "enforce_admins": data.get("enforce_admins", {}).get("enabled", False),
            }

    @staticmethod
    def filter_merged_prs_in_window(
        raw_prs: List[Dict[str, Any]],
        period_start: datetime,
        period_end: datetime,
    ) -> List[Dict[str, Any]]:
        """Filters merged PRs strictly within the observation window."""
        valid_population = []
        for pr in raw_prs:
            merged_at_str = pr.get("merged_at")
            if not merged_at_str:
                continue

            merged_at = datetime.fromisoformat(merged_at_str.replace("Z", "+00:00"))
            if period_start <= merged_at <= period_end:
                valid_population.append({
                    "pr_number": pr["number"],
                    "title": pr["title"],
                    "url": pr.get("html_url", ""),
                    "author": pr.get("user", {}).get("login"),
                    "merged_at": merged_at.isoformat(),
                    "merge_commit_sha": pr.get("merge_commit_sha"),
                })
        return valid_population
