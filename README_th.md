# คู่มือใช้งาน JCtrans Scraper ผ่าน Docker/Portainer

## โครงสร้างโปรเจกต์
```
jctrans-playwright-scraper/
├── Dockerfile
├── docker-compose.yml
├── scrape_jctrans.py
├── cookies.json
├── output/  (โฟลเดอร์สำหรับไฟล์ Excel)
└── README_th.md
```

## วิธีใช้งานผ่าน Portainer Stack

1. เปิด **Portainer** → ไปที่ **Stacks** → คลิก **Add stack**
2. ตั้งชื่อ Stack เช่น `jctrans-scraper`
3. วางเนื้อหาในไฟล์ `docker-compose.yml` ลงในช่อง **Web editor**
4. คลิก **Deploy the stack**
5. ระบบจะ Build container และ Run สคริปต์อัตโนมัติ
6. เมื่อรันเสร็จ ตรวจสอบไฟล์ Excel ที่ **output/contracts_page_1.xlsx**

## วิธีปรับแต่ง Cookie

- เปิด Chrome → Login เข้า JCtrans → DevTools → Application → Storage → Cookies
- คลิกขวา → Copy value ของ cookie แต่ละตัว
- แก้ไขค่าในไฟล์ `cookies.json`

## วิธีตรวจสอบผลลัพธ์

- เข้าไปที่โฟลเดอร์ `output/`
- เปิดไฟล์ `contracts_page_1.xlsx` ด้วย Excel เพื่อดูข้อมูล

## การรันซ้ำหน้า
- ในอนาคตถ้าต้องการให้ดึงหลายหน้าหรือเฉพาะหน้าใหม่ สามารถปรับโค้ดใน `scrape_jctrans.py` ได้ทันที
