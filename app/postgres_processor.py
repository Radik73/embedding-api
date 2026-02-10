import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any, List
from app.settings.db_credentials import *


class PostgresProcessor:
    def __init__(self):
        self.connection_params = {
            "host": postgres_host,
            "port": postgres_port,
            "database": postgres_db,
            "user": postgres_user,
            "password": postgres_password
        }
        print("🔍 Подключаюсь к PostgreSQL...")
        self._ensure_table_exists()
        print("✅ PostgreSQL инициализирован")

    def _get_connection(self):
        return psycopg2.connect(**self.connection_params)


    # app/postgres_processor.py
    def _ensure_table_exists(self):
        """Создаёт таблицы, если они не существуют"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Таблица документов
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        content_id BIGINT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        content_text TEXT NOT NULL,
                        content_hash TEXT NOT NULL,
                        url TEXT,
                        header TEXT,
                        document_id TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Индексы
                cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(user_id, content_hash);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_document_id ON documents(document_id);")
                
                # Таблица кластеров
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_clusters (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        cluster_label TEXT NOT NULL,
                        description TEXT NOT NULL,
                        centroid_vector FLOAT8[],
                        created_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(user_id, cluster_label)
                    )
                """)
                
                conn.commit()
        print("✅ Таблицы 'documents' и 'user_clusters' готовы")


    def save_document(self, content_id: int, user_id: int, content_text: str, 
                content_hash: str, url: str = "", header: str = "", 
                document_id: str = None):
        """Сохраняет документ в PostgreSQL"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO documents 
                        (content_id, user_id, content_text, content_hash, url, header, document_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (content_id, user_id, content_text, content_hash, url, header, document_id))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Ошибка сохранения документа: {e}")
            return False


    def get_document(self, content_id: int) -> Optional[Dict[str, Any]]:
        """Получает полный документ по content_id"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM documents WHERE content_id = %s",
                        (content_id,)
                    )
                    return cur.fetchone()
        except Exception as e:
            print(f"❌ Ошибка чтения из PostgreSQL: {e}")
            return None

    def get_user_documents(self, user_id: int, limit: int = 100) -> list:
        """Получает список документов пользователя (без полного текста для экономии)"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT content_id, url, header, created_at
                        FROM documents
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (user_id, limit))
                    return cur.fetchall()
        except Exception as e:
            print(f"❌ Ошибка списка документов: {e}")
            return []
        

    def get_content_id_by_hash(self, user_id: int, content_hash: str) -> Optional[int]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT content_id FROM documents WHERE user_id = %s AND content_hash = %s",
                        (user_id, content_hash)
                    )
                    row = cur.fetchone()
                    return row[0] if row else None
        except Exception as e:
            print(f"❌ Ошибка при проверке хеша: {e}")
            return None
        
    
    def save_cluster_centroids(self, user_id: int, centroids: Dict[str, dict]):
        """Сохраняет центроиды и описания кластеров"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Удаляем старые кластеры пользователя
                cur.execute("DELETE FROM user_clusters WHERE user_id = %s", (user_id,))
                
                # Вставляем новые
                for label, data in centroids.items():
                    cur.execute("""
                        INSERT INTO user_clusters (user_id, cluster_label, centroid_vector, description)
                        VALUES (%s, %s, %s, %s)
                    """, (user_id, label, data["centroid"], data.get("description", "")))
                conn.commit()


    def get_cluster_centroids(self, user_id: int) -> Dict[str, dict]:
        """Получает центроиды кластеров пользователя"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT cluster_label, centroid_vector, description FROM user_clusters WHERE user_id = %s",
                        (user_id,)
                    )
                    return {
                        row["cluster_label"]: {
                            "centroid": row["centroid_vector"],
                            "description": row["description"]
                        }
                        for row in cur.fetchall()
                    }
        except Exception as e:
            print(f"❌ Ошибка загрузки кластеров: {e}")
            return {}
        
        
    def get_documents_by_content_ids(self, content_ids: List[int], user_id: int):
        """Получает полные документы из PostgreSQL по списку content_id"""
        if not content_ids:
            return []
            
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    placeholders = ','.join(['%s'] * len(content_ids))
                    cur.execute(f"""
                        SELECT content_id, user_id, content_text, url, header, document_id
                        FROM documents 
                        WHERE content_id IN ({placeholders}) AND user_id = %s
                    """, content_ids + [user_id])
                    
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Ошибка получения документов: {e}")
            return []
        
    def clear_test_data(self, min_user_id=9000):
        """Удаляет тестовые данные"""
        self.conn.execute(f"DELETE FROM documents WHERE user_id >= {min_user_id};")
        self.conn.execute(f"DELETE FROM user_clusters WHERE user_id >= {min_user_id};")
        self.conn.commit()