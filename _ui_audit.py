import re
import json
import urllib.request

base = 'http://127.0.0.1:7860'
html = urllib.request.urlopen(base + '/ui', timeout=20).read().decode('utf-8', 'ignore')

routes = {}
for p in ['/', '/ui', '/health', '/state', '/report']:
    try:
        r = urllib.request.urlopen(base + p, timeout=20)
        routes[p] = getattr(r, 'status', 200)
    except Exception as e:
        routes[p] = str(e)

onclick_calls = re.findall(r'onclick="([a-zA-Z_][a-zA-Z0-9_]*)\(', html)
defs = set(re.findall(r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', html))
missing_defs = sorted(set(onclick_calls) - defs)

hooks = {k: (k in html) for k in [
    'startNewRun', 'runAction', 'downloadRunReport', 'showScreen', 'selectTask',
    'runner-step-log', 'governance-ci-gates', 'leaderboard-list', 'recent-runs-list'
]}

res = {}
reset_req = urllib.request.Request(
    base + '/reset',
    data=json.dumps({'task_id': 'easy_missing_and_dupes'}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
reset = json.loads(urllib.request.urlopen(reset_req, timeout=20).read().decode())
res['reset_ok'] = reset.get('task_id') == 'easy_missing_and_dupes'

step_req = urllib.request.Request(
    base + '/step',
    data=json.dumps({'operation': 'clean_missing', 'target_columns': ['amount'], 'parameters': {}}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
step = json.loads(urllib.request.urlopen(step_req, timeout=20).read().decode())
res['step_ok'] = ('observation' in step and 'reward' in step and 'info' in step)
res['reward_has_total_field'] = ('total' in step.get('reward', {}))
res['governance_in_step'] = ('governance' in step.get('info', {}))

for op, cols in [
    ('deduplicate', []),
    ('cast_type', ['amount']),
    ('normalize_categories', ['region']),
    ('cap_outliers', ['amount']),
    ('validate_constraints', []),
    ('submit', []),
]:
    req = urllib.request.Request(
        base + '/step',
        data=json.dumps({'operation': op, 'target_columns': cols, 'parameters': {}}).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    payload = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
    if payload.get('done'):
        break

eval_req = urllib.request.Request(
    base + '/evaluate',
    data=json.dumps({'thresholds': {}}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
ev = json.loads(urllib.request.urlopen(eval_req, timeout=20).read().decode())
res['evaluate_ok'] = ('decision' in ev and 'gates' in ev)

ui_gaps = {
    'export_pdf_button_no_handler': ('Export PDF</button>' in html and 'onclick="exportPdf' not in html),
    'config_nav_static': ('API Settings</div>' in html and "showScreen('api" not in html),
}

print(json.dumps({
    'routes': routes,
    'onclick_calls': sorted(set(onclick_calls)),
    'missing_onclick_defs': missing_defs,
    'hooks': hooks,
    'api_flow': res,
    'ui_gaps': ui_gaps,
}, indent=2))
