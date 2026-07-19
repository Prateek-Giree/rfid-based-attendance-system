# Smart Attendance Management System (SAMS)

A modern, fast, and responsive web application built with Django 5 and Tailwind CSS for managing student attendance via RFID devices and manual teacher inputs.

## Features

- **Role-Based Access Control**: Separate dashboards and permissions for Admins and Teachers.
- **Classroom & Student Management**: Complete CRUD operations with soft deletes and unique validations.
- **Teacher Management**: Secure teacher accounts with password management.
- **RFID Device Integration**: Register and manage IoT RFID scanners with API key authentication.
- **Attendance Tracking**: 
  - Automated logging via RFID API endpoint.
  - Manual bulk attendance marking for teachers.
- **Analytics Dashboard**: Rich, interactive charts using Chart.js powered by HTMX for seamless updates without page reloads.
  - Attendance Trends, Classroom Rates, Present vs Absent, and more.
- **Reports & Export**: Generate comprehensive attendance reports and export data to CSV.
- **Student Portal**: Public-facing portal for students to check their attendance history using their RFID UID.

## Tech Stack

- **Backend**: Django 5, Python 3
- **Database**: PostgreSQL (Supabase recommended)
- **Frontend**: Tailwind CSS, HTMX, Alpine.js (for simple interactions), Vanilla JS
- **UI Components**: Lucide Icons, SweetAlert2 for notifications
- **Data Visualization**: Chart.js

## Project Architecture

- **Class-Based Views (CBV)**: Django views are kept thin.
- **Service Layer Pattern**: All business logic (creation, validation, analytics aggregation) lives in dedicated service files (e.g., `StudentService`, `AttendanceService`).
- **Form Validation**: 3-layer validation (HTML5 attributes -> JS UX feedback -> Django Form clean methods).

## Installation and Setup

### Prerequisites

- Python 3.10+
- PostgreSQL

### Local Development Setup

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd rfid-based-attendance-system
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python -m venv env
   # On Windows:
   env\Scripts\activate
   # On macOS/Linux:
   source env/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   
   Create a `.env` file in the root directory. You can use the provided template or set the following variables:

   ```env
   SECRET_KEY=your-django-secret-key
   DEBUG=True
   DATABASE_URL=postgres://user:password@localhost:5432/sams_db
   ```

5. **Run Migrations:**

   ```bash
   python manage.py migrate
   ```

6. **Create Superuser (Admin):**

   ```bash
   python manage.py createsuperuser
   ```

7. **Run the Development Server:**

   ```bash
   python manage.py runserver
   ```

8. **Access the Application:**
   Open `http://127.0.0.1:8000` in your web browser.

## API Documentation

### RFID Scan Endpoint

Used by IoT devices to log an attendance scan.

- **URL**: `/api/rfid/scan/`
- **Method**: `POST`
- **Headers**:
  - `Content-Type: application/json`
  - `X-API-Key: <Device-API-Key>`
- **Payload**:
  ```json
  {
      "uid": "A1B2C3D4"
  }
  ```

## License

This project is proprietary and confidential.
