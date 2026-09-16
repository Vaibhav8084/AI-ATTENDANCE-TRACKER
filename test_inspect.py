import urllib.request, ssl, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 1. Zoho IAM signin iframe
url_iam = 'https://academia.srmist.edu.in/accounts/p/10002227248/signin?hide_fp=true&orgtype=40&service_language=en&dcc=true'
req = urllib.request.Request(url_iam, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        print('=== IAM SIGNIN HTML SNIPPET ===')
        inputs = re.findall(r'<input.*?>', html, re.IGNORECASE)
        print('Inputs in IAM:', inputs[:10])
        forms = re.findall(r'<form.*?>', html, re.IGNORECASE)
        print('Forms in IAM:', forms)
except Exception as e:
    print('Error IAM:', e)

# 2. Staff Finder search
url_sf = 'https://www.srmist.edu.in/staff-finder/'
req_sf = urllib.request.Request(url_sf, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
try:
    with urllib.request.urlopen(req_sf, context=ctx, timeout=15) as resp:
        html_sf = resp.read().decode('utf-8', errors='ignore')
        print('\n=== STAFF FINDER FORMS ===')
        forms_sf = re.findall(r'<form.*?>.*?</form>', html_sf, re.DOTALL | re.IGNORECASE)
        for f in forms_sf:
            print('Form:', f[:300])
except Exception as e:
    print('Error Staff Finder:', e)
