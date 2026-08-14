import os
import sys

# إضافة جذر المشروع لمسار البحث لضمان عمل الاستيرادات
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.containers import ApplicationScope

def print_banner():
    print("\nESA-Lite CLI 2.1.0")

def list_tokens_action(engine):
    print("\n[1] Scanning for tokens...")
    result = engine.list_tokens()
    if result['success']:
        tokens = result['data']
        if not tokens:
            print("   No tokens found.")
            return []
        for i, token in enumerate(tokens):
            status = "Logged In" if token.get('logged_in') else "Locked"
            dll = token.get('dll_path') or "n/a"
            print(f"   {i+1}. {token['label']} (Serial: {token['serial']}) [{status}]")
            print(f"       dll: {dll}")
        return tokens
    else:
        print(f"   Error: {result['message']}")
        return []

def run_cli():
    # Logger is configured once in main.py (CLI-DEBUG).
    print("Initializing Core Engine...")
    try:
        # اكتفاء بطلب المحرك، هو سيتكفل بالـ HealthCheck داخلياً
        engine = ApplicationScope.get_engine()
    except Exception as e:
        print(f"Failed to initialize engine: {e}")
        return

    
    print_banner()
    
    try:
        while True:
            print("\nMain Menu:")
            print("1. List & Scan Tokens")
            print("2. Login (Verify PIN)")
            print("3. View Certificate Info")
            print("4. View Certificate (System Viewer)")
            print("5. Change PIN")
            print("6. Logout")
            print("7. Health / available drivers")
            print("0. Exit")
            
            choice = input("\nSelect an option: ")
            
            if choice == '1':
                list_tokens_action(engine)
                
            elif choice in ['2', '3', '4', '5', '6']:
                tokens = list_tokens_action(engine)
                if not tokens: continue
                
                raw_idx = input(f"Select token (1-{len(tokens)}) [or Enter to cancel]: ")
                if not raw_idx.strip(): continue
                
                try:
                    idx = int(raw_idx) - 1
                    if idx < 0 or idx >= len(tokens): raise ValueError
                except ValueError:
                    print("   Invalid selection.")
                    continue

                serial = tokens[idx]['serial']
                
                if choice == '2':
                    pin = input("Enter PIN: ")
                    res = engine.login_token(serial, pin)
                    print(f"   Result: {'OK' if res['success'] else 'FAIL'} {res['message']}")
                    
                elif choice == '3':
                    res = engine.get_certificate_info(serial)
                    if res['success']:
                        data = res['data']
                        print(f"\n   Certificate Details:")
                        print(f"   - Subject: {data['subject']}")
                        print(f"   - Issuer: {data['issuer']}")
                        print(f"   - Expiry: {data['expiry']}")
                    else:
                        print(f"   Error: {res['message']} (Code: {res['error_code']})")
                        
                elif choice == '4':
                    res = engine.get_certificate_view_path(serial)
                    if res['success']:
                        path = res['data']
                        print(f"   Opening certificate file: {path}")
                        if sys.platform == 'win32':
                            os.startfile(path)
                    else:
                        print(f"   Error: {res['message']}")

                elif choice == '5':
                    old_pin = input("Enter current PIN: ")
                    new_pin = input("Enter new PIN: ")
                    confirm = input("Confirm new PIN: ")
                    if new_pin != confirm:
                        print("   Error: PIN mismatch.")
                        continue
                    res = engine.change_pin(serial, old_pin, new_pin)
                    print(f"   Result: {'OK' if res['success'] else 'FAIL'} {res['message']}")

                elif choice == '6':
                    res = engine.logout_token(serial)
                    print(f"   Result: {'OK' if res['success'] else 'FAIL'} {res['message']}")

            elif choice == '7':
                report = ApplicationScope.get_health_check().run_full_check()
                print("\n[HEALTH REPORT]")
                print(f"  Status: {report.get('status')}")
                print(f"  Smart Card: {'RUNNING' if report.get('is_smart_card_service_running') else 'STOPPED'}")
                available = report.get('available_drivers') or []
                if available:
                    print("  Available drivers:")
                    for path in available:
                        print(f"    - {path}")
                else:
                    print("  Available drivers: (none)")
                found = report.get("drivers_found") or {}
                for name, entry in found.items():
                    loadable = entry.get("is_loadable")
                    src = entry.get("source") or entry.get("error") or "n/a"
                    print(f"  {name}: loadable={loadable} ({src})")
                codes = report.get("error_codes") or []
                if codes:
                    print(f"  Error codes: {[getattr(c, 'value', c) for c in codes]}")
                if report.get("issues"):
                    print(f"  Issues: {report['issues']}")

            elif choice == '0':
                print("Shutting down...")
                ApplicationScope.shutdown()
                break
            else:
                print("Invalid option.")
    except KeyboardInterrupt:
        print("\n[CLI] Interrupted by user. Exiting...")
        ApplicationScope.shutdown()

if __name__ == "__main__":
    try:
        run_cli()
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal CLI Error: {e}")
        sys.exit(1)