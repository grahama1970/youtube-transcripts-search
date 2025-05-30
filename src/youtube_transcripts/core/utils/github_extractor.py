import re
from typing import List, Dict

def extract_github_repos(transcript: str) -> List[Dict[str, str]]:
    """Extract GitHub repositories mentioned in transcripts"""
    
    patterns = [
        # Direct GitHub URLs
        r'github\.com/([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)',
        
        # Verbal mentions
        r'(?:the\s+)?code\s+is\s+(?:at|on)\s+github[:\s]+([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)',
        r'check\s+out\s+([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)\s+on\s+github',
        r'github\s+repository[:\s]+([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)',
        
        # Common patterns
        r'(?:my|our|the)\s+([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)\s+(?:repo|repository)',
    ]
    
    repos = set()
    for pattern in patterns:
        matches = re.findall(pattern, transcript, re.IGNORECASE)
        repos.update(matches)
    
    # Validate and format results
    results = []
    for repo in repos:
        if '/' in repo and len(repo.split('/')) == 2:
            user, name = repo.split('/')
            results.append({
                "full_name": repo,
                "user": user,
                "name": name,
                "url": f"https://github.com/{repo}"
            })
    
    return results

# Test function
if __name__ == "__main__":
    test_transcript = """
    Today we'll look at the VERL implementation. You can find the code 
    at github.com/volcengine/verl. Also check out bytedance/verl-examples 
    on GitHub for more examples.
    """
    
    repos = extract_github_repos(test_transcript)
    for repo in repos:
        print(f"Found: {repo['full_name']} - {repo['url']}")