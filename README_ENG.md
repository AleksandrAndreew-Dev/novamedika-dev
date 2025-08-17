---

# **Novamedika Drug Availability Monitoring Platform**

---

## **Project Overview**
A platform for real-time display of drug availability across the *Novamedika* pharmacy network.  
The system includes:
- Uploading and processing data from CSV files  
- Searching for drugs and pharmacies  
- Integration with **Elasticsearch** for fast search  
- Background task processing with **Celery**  
- **REST API** for integrations  

---

## **Technology Stack**
- **Backend**: Django (Python)  
- **Database**: PostgreSQL  
- **Search**: Elasticsearch 7.x  
- **Asynchronous Tasks**: Celery + RabbitMQ + Redis  
- **Caching**: Redis  
- **Web Server**: Nginx  
- **Orchestration**: Docker Compose  
- **Monitoring**: Flower  

---

## **Key Features**

1. **Data Upload**
   - Accept CSV files via API  
   - Asynchronous data processing  
   - Data validation and normalization  
   - Real-time updates to Elasticsearch  

2. **Drug Search**
   - Search by name, dosage form, manufacturer  
   - Filter by city  
   - Grouped results  

3. **Pharmacy Management**
   - View list of pharmacies  
   - Detailed pharmacy information  
   - Update pharmacy data  

4. **Administration**
   - Task monitoring via Flower  
   - Elasticsearch index management  
   - File processing logs  

---

## **Project Setup**

### **Requirements**
- Docker  
- Docker Compose  

### **Instructions**
1. Copy the environment file:  
   ```bash
   cp .env.example .env
   ```
   Fill in the values in `.env`

2. Start in development mode:  
   ```bash
   docker-compose -f docker-compose.dev.yml up --build
   ```

3. Start in production mode:  
   ```bash
   docker-compose -f docker-compose.prod.yml up --build -d
   ```

---

## **API Endpoints**

### Upload CSV
```
POST /api/<pharmacy_name>/<pharmacy_number>/
```
Parameters:
- `file`: CSV file with data

### Check Task Status
```
GET /api/check_status/<task_id>/
```

### Search for Drugs
```
GET /search_products?name=...&city=...
```

---

## **Key Configurations**

### Elasticsearch
Configuration in `elasticsearch.yml`:
- Security disabled for development  
- Optimized memory settings  
- Docker healthcheck configured  

### Nginx
Settings in `nginx.conf`:
- HTTPS redirect  
- Static and media file serving  
- Reverse proxy to Django  
- Increased file upload limit (`client_max_body_size 50M`)  

---

## **Periodic Tasks**

Celery tasks (located in `pharmacies/tasks.py`):
1. `update_elasticsearch_index` – partial index update (every 5 minutes)  
2. `full_elasticsearch_resync` – full reindexing (on demand)  
3. `update_pharmacy_city_in_index` – update pharmacy data  

---

## **Data Models**

### Main Entities (`models.py`)
1. **Pharmacy**
   - Name, number, city, address  
   - Unique UUID identifier  

2. **Product**
   - Name, dosage form, manufacturer  
   - Prices (retail, wholesale)  
   - Linked to a pharmacy  
   - Indexes for search optimization  

3. **CsvProcessingTask**
   - Execution status  
   - Processing results  
   - Linked to a pharmacy  

---

## **Implementation Details**

1. **Elasticsearch Optimization**
   - Custom mappings in `documents.py`  
   - Batch data processing  
   - Container healthcheck  

2. **CSV Processing**
   - Automatic encoding detection  
   - Data transformation  
   - Duplicate removal  
   - Atomic operations  

3. **Security**
   - HTTPS in production  
   - Cookie protection (SameSite, Secure)  
   - Authentication in Flower  

---

## **Monitoring**
Available at: `http://localhost:5555` (Flower)  
- View running tasks  
- Monitor workers  
- Manage periodic tasks  
