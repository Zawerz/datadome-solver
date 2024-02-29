import time
import json
import requests

API_KEY = "your capsolver.com api key"
# TODO: YOUR_PROXY
PROXY = "your proxy"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
SITE_URL_WITH_DATADOME = "https://www.footlocker.com/"

HEADERS_TEMPLATE = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'en,en-US;q=0.9',
    'cache-control': 'max-age=0',
    'dnt': '1',
    'sec-ch-device-memory': '8',
    'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
    'sec-ch-ua-arch': '"x86"',
    'sec-ch-ua-full-version-list': '"Google Chrome";v="119.0.6045.200", "Chromium";v="119.0.6045.200", "Not?A_Brand";v="24.0.0.0"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-model': '""',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'sec-gpc': '1',
    'upgrade-insecure-requests': '1',
    'user-agent': USER_AGENT,
    'referer': SITE_URL_WITH_DATADOME  
}

def format_proxy(px: str):
    if '@' not in px:
        sp = px.split(':')
        if len(sp) == 4:
            px = f'{sp[2]}:{sp[3]}@{sp[0]}:{sp[1]}'
    return {"http": f"http://{px}", "https": f"http://{px}"}

def get_page_with_cookie(url, cookie=None):
    headers = HEADERS_TEMPLATE.copy()
    if cookie:
        headers['cookie'] = f"datadome={cookie}"
    try:
        response = requests.get(url, headers=headers, proxies=format_proxy(PROXY), timeout=(20, 20), verify=False)
        print(response.text)
        print(response.status_code)
        return response
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None

def extract_captcha_url(response):
    if response.status_code == 403 or "geo.captcha-delivery.com" in response.text:
        if 'dd=' in response.text:
            dd = response.text.split('dd=')[1]
            dd = dd.split('</script')[0]
            dd = json.loads(dd.replace("'", '"'))
            cid = response.headers.get('Set-Cookie').split('datadome=')[1]
            cid = cid.split(';')[0]
            return f"https://geo.captcha-delivery.com/captcha/?initialCid={dd['cid']}&hash={dd['hsh']}&cid={cid}&t={dd['t']}&referer={SITE_URL_WITH_DATADOME}&s={dd['s']}&e={dd['e']}"
        else:
            possible_paths = ["/captcha/", "/interstitial/"]
            for path in possible_paths:
                start_index = response.text.find(f"https://geo.captcha-delivery.com{path}")
                if start_index != -1:
                    end_index = response.text.find('"', start_index)
                    return response.text[start_index:end_index]
    return "Not DataDome Captcha / Challenge found"

def call_capsolver(web_url, captcha_url):
    data = {
        "clientKey": API_KEY,
        "task": {
            "type": 'DatadomeSliderTask',
            "websiteURL": web_url,
            "captchaUrl": captcha_url,
            "userAgent": USER_AGENT,
            "proxy": PROXY
        }
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    res = requests.post('https://api.capsolver.com/createTask', headers=headers, json=data, verify=False)
    resp = res.json()
    task_id = resp.get('taskId')
    if not task_id:
        print("create task failed:", res.text)
        return
    while True:
        time.sleep(1)
        data = {
            "clientKey": API_KEY,
            "taskId": task_id
        }
        res = requests.post('https://api.capsolver.com/getTaskResult', headers=headers, json=data, verify=False)
        resp = res.json()
        status = resp.get('status', '')
        if status == "ready":
            cookie = resp['solution']['cookie']
            cookie = cookie.split(';')[0].split('=')[1]
            print("successfully got cookie:", cookie)
            return cookie
        if status == "failed" or resp.get("errorId"):
            print("failed to solve datadome:", res.text)
            return
        print('solve datadome status:', status)

def test_register_page():
    response = get_page_with_cookie(SITE_URL_WITH_DATADOME)
    print("Getting captcha url")
    captcha_url = extract_captcha_url(response)
    print(captcha_url)
    if captcha_url and 't=bv' not in captcha_url:
        cookie = call_capsolver(SITE_URL_WITH_DATADOME, captcha_url)
        if cookie:
            get_page_with_cookie(SITE_URL_WITH_DATADOME, cookie)

if __name__ == '__main__':
    test_register_page()
