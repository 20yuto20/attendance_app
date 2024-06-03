from db_connection import get_db_connection

def get_total_break_duration(punch_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    query = "SELECT SUM(break_duration) AS total_break_duration FROM break_time WHERE punch_id = %s"
    cursor.execute(query, (punch_id,))
    result = cursor.fetchone()

    total_break_minutes = result[0] if result[0] else 0

    total_break_hours = int(total_break_minutes // 60)
    total_break_minutes = int(total_break_minutes % 60)

    cursor.close()
    connection.close()

    return total_break_hours, total_break_minutes