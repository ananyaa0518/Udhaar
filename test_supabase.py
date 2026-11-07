
from database.supabase_client import supabase

try:
    response = (
        supabase
        .table("customers")
        .select("*")
        .limit(5)
        .execute()
    )

    print("Supabase connected successfully!")
    print("Customers:", response.data)

except Exception as error:
    print("Supabase connection failed:")
    print(error)
