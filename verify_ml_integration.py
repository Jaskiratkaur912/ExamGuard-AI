#!/usr/bin/env python3
"""
ML Integration Verification Script
Run this to verify all ML components are properly integrated
"""

import os
import sys

def verify_ml_models():
    """Check if ML models exist in workspace root"""
    print("\n[1/5] Checking ML models...")
    
    required_files = [
        ('cheating_score.py', 'Cheating detection model'),
        ('exam_intelligence.py', 'Question randomization & answer grading'),
    ]
    
    all_found = True
    for filename, description in required_files:
        path = os.path.join('/workspaces/ExamGuard-AI', filename)
        if os.path.exists(path):
            print(f"  ✓ {filename} - {description}")
        else:
            print(f"  ✗ {filename} - {description} NOT FOUND")
            all_found = False
    
    return all_found


def verify_app_py():
    """Check if app.py has ML integration"""
    print("\n[2/5] Checking app.py integration...")
    
    app_path = '/workspaces/ExamGuard-AI/app.py'
    if not os.path.exists(app_path):
        print(f"  ✗ app.py not found at {app_path}")
        return False
    
    with open(app_path, 'r') as f:
        content = f.read()
    
    required_strings = [
        ('from cheating_score import compute_cheating_score', 'ML model import'),
        ('def browser_events_to_violation_log', 'Conversion helper'),
        ('/ml-dashboard', 'ML dashboard route'),
        ('/api/ml/cheating-analysis', 'ML API endpoint'),
    ]
    
    all_found = True
    for check_str, description in required_strings:
        if check_str in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} NOT FOUND")
            all_found = False
    
    return all_found


def verify_templates():
    """Check if ML templates exist"""
    print("\n[3/5] Checking templates...")
    
    templates = [
        'ml_dashboard_main.html',
        'ml_exam_analysis.html',
        'ml_student_detail.html',
    ]
    
    all_found = True
    for template in templates:
        path = os.path.join('/workspaces/ExamGuard-AI/templates', template)
        if os.path.exists(path):
            print(f"  ✓ {template}")
        else:
            print(f"  ✗ {template} NOT FOUND")
            all_found = False
    
    return all_found


def verify_imports():
    """Test if imports work"""
    print("\n[4/5] Testing imports...")
    
    try:
        sys.path.insert(0, '/workspaces/ExamGuard-AI')
        from cheating_score import compute_cheating_score
        print(f"  ✓ Successfully imported: compute_cheating_score")
    except ImportError as e:
        print(f"  ✗ Failed to import cheating_score: {e}")
        return False
    
    try:
        from exam_intelligence import QuestionBankRandomizer
        print(f"  ✓ Successfully imported: QuestionBankRandomizer")
    except ImportError as e:
        print(f"  ✗ Failed to import exam_intelligence: {e}")
        return False
    
    return True


def verify_routes():
    """Check Flask routes in app.py"""
    print("\n[5/5] Checking Flask routes...")
    
    app_path = '/workspaces/ExamGuard-AI/app.py'
    with open(app_path, 'r') as f:
        content = f.read()
    
    routes = [
        ('/ml-dashboard', 'Main dashboard'),
        ('/ml-dashboard/exam', 'Exam analysis'),
        ('/ml-dashboard/student', 'Student detail'),
        ('/api/ml/cheating-analysis', 'Cheating API'),
        ('/api/ml/exam-statistics', 'Stats API'),
        ('/api/ml/browser-events', 'Events API'),
    ]
    
    all_found = True
    for route, description in routes:
        if f"@app.route('{route}" in content:
            print(f"  ✓ {route} - {description}")
        else:
            print(f"  ✗ {route} NOT FOUND")
            all_found = False
    
    return all_found


def main():
    print("=" * 60)
    print("ML INTEGRATION VERIFICATION")
    print("=" * 60)
    
    results = []
    
    results.append(("ML Models", verify_ml_models()))
    results.append(("App Integration", verify_app_py()))
    results.append(("Templates", verify_templates()))
    results.append(("Imports", verify_imports()))
    results.append(("Routes", verify_routes()))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_ok = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:.<40} {status}")
        if not result:
            all_ok = False
    
    print("=" * 60)
    
    if all_ok:
        print("\n✅ All checks passed! ML integration is ready.")
        print("\nNext steps:")
        print("1. Start Flask app: python app.py")
        print("2. Log in as admin")
        print("3. Visit: http://localhost:5000/ml-dashboard")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
