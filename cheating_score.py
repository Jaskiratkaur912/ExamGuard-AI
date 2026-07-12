"""
cheating_score.py  —  ExamGuard-AI  |  Drop next to homepg.py
================================================================
ML-based Cheating Risk Scorer — covers 18 edge cases.
No external libraries needed — pure Python stdlib only.
"""

import math
from datetime import datetime
from collections import Counter

VIOLATION_WEIGHTS = {
    "Multiple faces detected in camera frame":          0.95,
    "No face detected in camera frame":                 0.70,
    "Significant head turn away from screen detected":  0.55,
    "Face mismatch detected":                           0.92,
    "Identity change suspected":                        0.98,
    "Student switched tabs or minimized the window":    0.65,
    "Student exited fullscreen mode":                   0.60,
    "Browser window lost focus":                        0.25,
    "Paste attempt detected":                           0.88,
    "Copy attempt detected":                            0.52,
    "Cut attempt detected":                             0.48,
    "Right-click attempt detected":                     0.22,
    "Developer tools opened":                           0.85,
}

FACE_VIOLATIONS = {"Multiple faces detected in camera frame","No face detected in camera frame","Significant head turn away from screen detected","Face mismatch detected","Identity change suspected"}
BROWSER_VIOLATIONS = {"Student switched tabs or minimized the window","Student exited fullscreen mode","Browser window lost focus"}
INTERACTION_VIOLATIONS = {"Paste attempt detected","Copy attempt detected","Cut attempt detected","Right-click attempt detected","Developer tools opened"}


def compute_cheating_score(violation_log, exam_duration_minutes=60, answers=None, total_questions=0, exam_score_pct=None):
    edge_cases = _detect_edge_cases(violation_log, exam_duration_minutes, exam_score_pct)
    if not violation_log and not edge_cases:
        return _build_result(0.0, violation_log, {}, [], edge_cases)

    severity   = _severity(violation_log)
    burst      = _burst(violation_log)
    escalation = _escalation(violation_log)
    diversity  = _diversity(violation_log)
    timing     = _timing(violation_log, exam_duration_minutes)
    edge_bonus = sum(ec["bonus"] for ec in edge_cases)

    raw = severity + burst + escalation + diversity + timing + edge_bonus
    final = min(100.0, max(0.0, raw))

    breakdown = {
        "severity_score":    round(severity, 1),
        "burst_score":       round(burst, 1),
        "escalation_score":  round(escalation, 1),
        "diversity_score":   round(diversity, 1),
        "timing_score":      round(timing, 1),
        "edge_case_bonus":   round(edge_bonus, 1),
    }
    flags = _build_flags(violation_log, breakdown, edge_cases)
    return _build_result(final, violation_log, breakdown, flags, edge_cases)


def _severity(violations):
    counts = Counter()
    total = 0.0
    for v in violations:
        r = v.get("reason","")
        w = _weight(r)
        total += w * (0.7 ** counts[r])
        counts[r] += 1
    return 40 * (1 - math.exp(-total * 0.8))


def _burst(violations):
    ts = sorted(filter(None, (_parse(v.get("time")) for v in violations)))
    if len(ts) < 3: return 0.0
    max_w = max(sum(1 for t in ts[i:] if (t-ts[i]).total_seconds()<=60) for i in range(len(ts)))
    if max_w < 4: return 0.0
    return min(20.0, (max_w-3)*2.5)


def _escalation(violations):
    ts = sorted(filter(None, (_parse(v.get("time")) for v in violations)))
    if len(ts) < 4: return 0.0
    dur = (ts[-1]-ts[0]).total_seconds()
    if dur < 30: return 0.0
    mid = ts[0].timestamp() + dur/2
    first  = sum(1 for t in ts if t.timestamp() < mid)
    second = sum(1 for t in ts if t.timestamp() >= mid)
    ratio  = second / max(first,1)
    if ratio>=3.0: return 15.0
    if ratio>=2.0: return 10.0
    if ratio>=1.5: return 5.0
    return 0.0


def _diversity(violations):
    rs = {v.get("reason","") for v in violations}
    hits = sum([any(r in FACE_VIOLATIONS for r in rs), any(r in BROWSER_VIOLATIONS for r in rs), any(r in INTERACTION_VIOLATIONS for r in rs)])
    return {3:10.0,2:5.0,1:0.0}.get(hits,0.0)


def _timing(violations, dur_min):
    if not violations or dur_min<=0: return 0.0
    ts  = list(filter(None, (_parse(v.get("time")) for v in violations)))
    rs  = [v.get("reason","") for v in violations]
    if not ts: return 0.0
    start = min(ts); score = 0.0
    last_20_start = start.timestamp() + dur_min*60*0.8
    in_last = sum(1 for t in ts if t.timestamp()>=last_20_start)
    pct = in_last/len(ts)
    if pct>0.6: score+=10.0
    elif pct>0.4: score+=5.0
    early_high = sum(1 for t,r in zip(ts,rs) if (t-start).total_seconds()<=300 and _weight(r)>=0.75)
    if early_high>=2: score+=5.0
    elif early_high==1: score+=2.0
    return min(15.0, score)


def _detect_edge_cases(violations, dur_min, score_pct):
    cases = []
    reasons  = [v.get("reason","") for v in violations]
    ts       = sorted(filter(None, (_parse(v.get("time")) for v in violations)))
    rs_set   = set(reasons)
    counts   = Counter(reasons)

    # EC7: Silent perfect score
    if score_pct is not None and score_pct>=0.98 and not violations:
        cases.append({"name":"silent_perfect_score","description":"Perfect score with zero violations — statistically rare.","bonus":8.0,"severity":"medium"})

    # EC8: Camera blocked (many no-face, zero multi-face)
    nf = counts.get("No face detected in camera frame",0)
    mf = counts.get("Multiple faces detected in camera frame",0)
    if nf>=5 and mf==0:
        cases.append({"name":"camera_covered","description":f"Camera consistently shows no face ({nf}x) with no multi-face — possible camera blocking.","bonus":12.0,"severity":"high"})

    # EC9: Late single spike
    if ts and dur_min>0:
        start = min(ts); late_start = start.timestamp()+dur_min*60*0.9
        late_high = sum(1 for t,r in zip(ts,reasons) if t.timestamp()>=late_start and _weight(r)>=0.80)
        if late_high>=2 and len(violations)<=4:
            cases.append({"name":"last_minute_spike","description":"High-severity violations only at the very end — targeted last-minute lookup.","bonus":10.0,"severity":"high"})

    # EC10: Repeated paste
    paste = counts.get("Paste attempt detected",0)
    if paste>=5:
        cases.append({"name":"repeated_paste","description":f"Paste attempted {paste} times — systematic answer pasting.","bonus":15.0,"severity":"critical"})
    elif paste>=2:
        cases.append({"name":"multiple_paste","description":f"Paste attempted {paste} times.","bonus":6.0,"severity":"high"})

    # EC11: Multiple faces + paste combo
    if mf>=1 and paste>=1:
        cases.append({"name":"proxy_with_paste","description":"Multiple faces + paste — likely proxy test-taker feeding answers.","bonus":18.0,"severity":"critical"})

    # EC12: Early tab switch (first 2 min)
    if ts:
        start = min(ts)
        early_tab = sum(1 for t,r in zip(ts,reasons) if (t-start).total_seconds()<=120 and r=="Student switched tabs or minimized the window")
        if early_tab>=1:
            cases.append({"name":"early_tab_switch","description":"Tab switch within first 2 minutes — opened answer source immediately.","bonus":8.0,"severity":"high"})

    # EC13: Fullscreen abandoned + blur
    if counts.get("Student exited fullscreen mode",0)>=1 and counts.get("Browser window lost focus",0)>=3:
        cases.append({"name":"fullscreen_abandoned","description":"Exited fullscreen + repeated window blur — integrity environment abandoned.","bonus":7.0,"severity":"medium"})

    # EC14: Right-click + copy combo
    if counts.get("Right-click attempt detected",0)>=2 and counts.get("Copy attempt detected",0)>=1:
        cases.append({"name":"targeted_extraction","description":"Right-click + copy combo — targeted question text extraction.","bonus":10.0,"severity":"high"})

    # EC15: High density short exam
    if dur_min<=15 and len(violations)>=5:
        cases.append({"name":"high_density_short_exam","description":f"{len(violations)} violations in {dur_min}-minute exam — extreme density.","bonus":8.0,"severity":"high"})

    # EC16: Perfect score + paste
    if score_pct is not None and score_pct>=0.90 and paste>=2:
        cases.append({"name":"perfect_score_with_paste","description":f"Scored {int(score_pct*100)}% with {paste} paste attempts.","bonus":12.0,"severity":"critical"})

    # EC17: DevTools opened
    if counts.get("Developer tools opened",0)>=1:
        cases.append({"name":"devtools_opened","description":"DevTools opened — possible DOM inspection to reveal answer indices.","bonus":14.0,"severity":"high"})

    # EC18: Identity change
    if "Identity change suspected" in rs_set:
        cases.append({"name":"identity_change","description":"Face embedding mismatch — different person detected mid-exam.","bonus":25.0,"severity":"critical"})

    return cases


def _weight(r):
    if r in VIOLATION_WEIGHTS: return VIOLATION_WEIGHTS[r]
    for k,w in VIOLATION_WEIGHTS.items():
        if any(word in r.lower() for word in k.lower().split()[:3]):
            return w
    return 0.30


def _parse(s):
    if not s: return None
    for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ","%Y-%m-%dT%H:%M:%SZ","%Y-%m-%dT%H:%M:%S","%Y-%m-%d %H:%M:%S","%H:%M:%S"]:
        try: return datetime.strptime(s[:26].rstrip("Z"), fmt.rstrip("Z"))
        except ValueError: continue
    return None


def _build_flags(violations, breakdown, edge_cases):
    flags = []
    reasons = [v.get("reason","") for v in violations]
    face = sum(1 for r in reasons if r in FACE_VIOLATIONS)
    interact = sum(1 for r in reasons if r in INTERACTION_VIOLATIONS)
    browser = sum(1 for r in reasons if r in BROWSER_VIOLATIONS)
    if face>=3:     flags.append(f"{face} face detection events")
    if interact>=1: flags.append(f"{interact} copy/paste/interaction events")
    if browser>=3:  flags.append(f"{browser} browser integrity events")
    if breakdown.get("burst_score",0)>10:      flags.append("violation burst detected")
    if breakdown.get("escalation_score",0)>8:  flags.append("violation escalation pattern")
    if breakdown.get("timing_score",0)>8:      flags.append("suspicious timing pattern")
    for ec in edge_cases: flags.append(ec["name"].replace("_"," "))
    return flags


def _build_result(score, violations, breakdown, flags, edge_cases):
    score = round(score, 1)
    if score>=75:   rl,color = "CRITICAL","#ef4444"
    elif score>=50: rl,color = "HIGH",    "#f97316"
    elif score>=25: rl,color = "MEDIUM",  "#eab308"
    else:           rl,color = "LOW",     "#22c55e"
    reasons = [v.get("reason","") for v in violations]
    return {
        "score": score, "risk_level": rl, "color": color,
        "total_violations": len(violations),
        "breakdown": breakdown, "flags": flags, "edge_cases": edge_cases,
        "categories": {
            "face_detection":    sum(1 for r in reasons if r in FACE_VIOLATIONS),
            "browser_integrity": sum(1 for r in reasons if r in BROWSER_VIOLATIONS),
            "interaction":       sum(1 for r in reasons if r in INTERACTION_VIOLATIONS),
        },
        "summary": f"Risk {score}/100 ({rl}) — {len(flags)} signals detected"
    }


def rank_students_by_risk(submissions):
    results = []
    for email, sub in submissions.items():
        v = sub.get("violations",[])
        sc = sub.get("score"); tot = sub.get("total")
        pct = (sc/tot) if (sc is not None and tot) else None
        risk = compute_cheating_score(v, sub.get("duration_minutes",60), total_questions=tot or 0, exam_score_pct=pct)
        risk["student_email"] = email
        risk["exam_score"] = f"{sc}/{tot}" if sc is not None else "PDF"
        results.append(risk)
    return sorted(results, key=lambda x: x["score"], reverse=True)


if __name__=="__main__":
    test=[
        {"reason":"Student switched tabs or minimized the window","time":"2026-07-09T10:02:00Z"},
        {"reason":"Multiple faces detected in camera frame","time":"2026-07-09T10:40:00Z"},
        {"reason":"Paste attempt detected","time":"2026-07-09T10:40:10Z"},
        {"reason":"Paste attempt detected","time":"2026-07-09T10:40:20Z"},
        {"reason":"Paste attempt detected","time":"2026-07-09T10:40:30Z"},
        {"reason":"Copy attempt detected","time":"2026-07-09T10:40:35Z"},
        {"reason":"Student exited fullscreen mode","time":"2026-07-09T10:40:40Z"},
    ]
    r = compute_cheating_score(test, exam_duration_minutes=60, exam_score_pct=0.95)
    print(f"Score: {r['score']}/100  [{r['risk_level']}]")
    print(f"Flags: {r['flags']}")
    print(f"Edge cases: {[e['name'] for e in r['edge_cases']]}")