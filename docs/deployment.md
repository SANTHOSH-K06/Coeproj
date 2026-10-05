# Deployment Notes

## Local development

```bash
./start.sh
```

This command seeds the SQLite database if needed, starts the FastAPI backend, and starts the Vite frontend.

## API access

- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:5173

## Default accounts

- Admin: `admin@hospital.com` / `admin123`
- Staff: `staff@hospital.com` / `staff123`

## Environment assumptions

The project was validated on the current local machine using:

- Python 3.13.5
- Node.js 22.18.0
- React 19.2.8
- Vite 8.2.2

This should be kept in sync with any future environment changes.
