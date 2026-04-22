import json

with open('backend/data/jobs.json', 'r', encoding='utf-8') as f:
    jobs = json.load(f)

output = []
output.append(f"Total jobs: {len(jobs)}")

for i, j in enumerate(jobs[:5]):
    output.append(f"\n--- Job {i+1} ---")
    output.append(f"  company: {j.get('company_name', 'N/A')}")
    output.append(f"  role: {j.get('role_title', 'N/A')}")
    output.append(f"  job_url: {j.get('job_url', 'N/A')}")
    output.append(f"  company_website: {j.get('company_website', 'N/A')}")
    output.append(f"  apply_mode: {j.get('apply_mode', 'N/A')}")
    output.append(f"  verified_url: {j.get('verified_url', 'N/A')}")
    output.append(f"  url_verified: {j.get('url_verified', 'N/A')}")

has_job_url = sum(1 for j in jobs if j.get('job_url') and 'http' in str(j.get('job_url', '')))
has_company_url = sum(1 for j in jobs if j.get('company_website') and 'http' in str(j.get('company_website', '')))
output.append(f"\nJobs with job_url: {has_job_url}/{len(jobs)}")
output.append(f"Jobs with company_website: {has_company_url}/{len(jobs)}")

generic_urls = 0
for j in jobs:
    url = j.get('job_url', '')
    if url and ('http' in url):
        path = url.split('/')
        if len(path) <= 4 and not any(kw in url.lower() for kw in ['career', 'job', 'apply', 'lever', 'greenhouse', 'ashby', 'workday']):
            generic_urls += 1
output.append(f"Generic company URLs (not job-specific): {generic_urls}/{len(jobs)}")

with open('_job_report.txt', 'w') as f:
    f.write('\n'.join(output))

print("Written to _job_report.txt")
