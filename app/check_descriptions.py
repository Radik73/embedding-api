# check_descriptions.py
import subprocess

def main():
    try:
        # Выполняем psql команду напрямую
        cmd = [
            "sudo", "-u", "postgres",
            "psql", "myapp_db", "-t", "-A", "-c",
            "SELECT user_id, cluster_label, description FROM user_clusters;"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        lines = result.stdout.strip().split('\n')
        if not lines or lines[0] == '':
            print("❌ В таблице user_clusters нет данных.")
            return
        
        print("✅ Описания кластеров:")
        print("-" * 60)
        for line in lines:
            parts = line.split('|')
            if len(parts) == 3:
                user_id, cluster_label, description = [p.strip() for p in parts]
                print(f"User {user_id} | Кластер {cluster_label} | {description}")
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка выполнения SQL: {e.stderr}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()