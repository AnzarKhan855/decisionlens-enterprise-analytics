import urllib.request
import json

def test_batch():
    url = "http://127.0.0.1:8000/api/v1/upload/batch"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"

    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="files"; filename="sales_batch1.csv"\r\n'
        'Content-Type: text/csv\r\n\r\n'
        'item_id,date,sales,store\r\nHOBBIES_1_001,2026-01-01,15,CA_1\r\n'
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="files"; filename="sales_batch2.csv"\r\n'
        'Content-Type: text/csv\r\n\r\n'
        'item_id,date,sales,store\r\nHOBBIES_1_002,2026-01-02,25,CA_2\r\n'
        f"--{boundary}--\r\n"
    ).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )

    try:
        res = urllib.request.urlopen(req)
        print("BATCH UPLOAD RESPONSE:", res.getcode(), res.read().decode('utf-8'))
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    test_batch()
