# ResourceHub

A web application for a college to manage events and shared resources
(auditoriums, labs, projectors, microphones, cameras, computers, etc.).

Built with Flask, SQLAlchemy, SQLite, Jinja2, and Tailwind CSS.

---

## Features

- Event management (create, edit, cancel, filter by status/date)
- Resource management (add, edit, activate/deactivate)
- Resource requests with existence/active/time/suitability validation
- Conflict-free double-booking prevention
- Automatic suggestion of suitable alternative resources
- Atomic multi-resource allocation (all-or-nothing, transactional)
- Approval workflow (Pending → Approved/Rejected, with cancellation)
- **Role-based authentication**: Admin and Organizer accounts with
  different permissions (see below)

---

## 1. Installation & Setup

### Requirements

- Python 3.10+
- pip

### Steps

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd ResourceHub

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) copy the env example and adjust values
cp .env.example .env

# 5. Seed the database with an admin account, a demo organizer
#    account, and sample resources
python seed.py

# 6. Run the application
python run.py                   # or: flask --app app run
```

The app will be available at `http://127.0.0.1:5000`.

### Production deployment

A `Procfile` is included for platforms that support Gunicorn:

```bash
gunicorn run:app
```

Set a strong random `SECRET_KEY` in the deployment environment and set
`DATABASE_URL` to your managed database connection string. Do not deploy
the demo credentials from `seed.py` unchanged.

### Demo accounts (created by `seed.py`)

| Role      | Email                        | Password      |
|-----------|-------------------------------|----------------|
| Admin     | admin@resourcehub.edu         | admin123       |
| Organizer | organizer@resourcehub.edu     | organizer123   |

Change or remove these before deploying anywhere public.

---

## 2. Database Setup

The app uses SQLite via SQLAlchemy. On startup, `create_app()` calls
`db.create_all()`, which creates all tables automatically from the
models in `app/models.py` if they don't already exist — there is no
separate migration step required for a fresh install.

The database file is created at `instance/resource_allocation.db` by
default. To reset the database completely (e.g. after changing a
model), delete that file and re-run `python seed.py`.

If you need a different database (e.g. Postgres for a hosted
deployment), set the `DATABASE_URL` environment variable to a valid
SQLAlchemy connection string before starting the app; it overrides
the SQLite default.

This project does not use a migration tool (like Alembic/Flask-Migrate)
since the schema is small and stable for the scope of this assignment;
`db.create_all()` combined with deleting the SQLite file is sufficient
for development and grading.

---

## 3. Authentication & Roles

The system has two roles: **Admin** and **Organizer**.

- Every page in the app requires being logged in, except
  `/auth/login` and `/auth/register`.
- New accounts created through the public **Register** page are
  always Organizer accounts. Admin accounts are not self-serve — they
  are provisioned via `seed.py` (or by inserting a `User` row with
  `role=Role.ADMIN` directly) so that nobody can grant themselves
  admin rights through the sign-up form.

### Admin responsibilities & access

- Add, edit, activate, and deactivate resources
- View, approve, or reject every resource request in the system
- Cancel any allocation (which releases the resource)
- View and manage every event and request, regardless of who
  created it

### Organizer responsibilities & access

- Create, edit, and cancel their **own** events only
- Request resources for their **own** events only
- View the status and allocation history of their **own**
  events/requests only
- View resource availability (read-only) to plan requests
- Cannot approve/reject requests, and cannot manage resources

Attempting to access an admin-only page, or another organizer's
event/request, as an Organizer returns a `403 Forbidden` page rather
than exposing or modifying the data. Visiting any page while logged
out redirects to the login page.

---

## 4. How Conflict Detection Works

Double-booking prevention lives in `app/services/booking.py`
(`find_conflicts`). When a resource is requested for a time window:

1. The system looks up all existing, non-cancelled allocations for
   that specific resource.
2. For each existing allocation, it checks for a standard interval
   overlap:
   `existing_start < new_end AND existing_end > new_start`.
   This means a booking ending exactly when another begins (e.g.
   10:00–14:00 followed by 14:00–16:00) is **allowed**, since the
   intervals don't actually overlap.
3. Each resource can optionally have a `buffer_minutes` setting
   (e.g. time needed to reset a lab or auditorium between events);
   this buffer is added to the edges of the existing booking before
   the overlap check, so back-to-back bookings can be required to
   leave a gap if the resource needs one.
4. If any overlap is found, the request (or that specific resource
   within a multi-resource request) is rejected.

Because an event can request **multiple** resources at once, the
whole allocation is wrapped in a **database transaction**
(`allocate_request` in `app/services/booking.py`): every requested
resource is validated first (existence, active status, suitability,
and conflict-free availability); only if **all** of them pass does
the transaction commit and create the allocations. If even one
resource fails, the entire transaction is rolled back and **no**
resources are allocated — preventing the partial-allocation problem
described in the assignment (e.g. Auditorium + Projector available,
but Microphone unavailable → nothing gets allocated).

---

## 5. How Alternative Resources Are Selected

When a requested resource is unavailable or unsuitable, the
alternative-resource logic (`app/services/alternatives.py`) looks for
a replacement that is:

1. **Active** — inactive resources are never suggested.
2. **The correct type** — a projector is only replaced with another
   projector, a hall with another hall, etc.
3. **Suitable capacity** — for capacity-bound resources (halls, labs),
   the alternative's capacity must be greater than or equal to the
   event's expected attendance.
4. **Available at the requested time** — the same conflict check used
   for booking (`find_conflicts`) is run against each candidate, so
   only resources with no overlapping booking are suggested.

Candidates that pass all four checks are ranked so that the
**smallest suitable capacity** is suggested first (i.e. the closest
match to what's actually needed, rather than always suggesting the
biggest hall available) and returned to the user as suggestions,
without automatically booking them — the organizer or admin still
has to submit/approve the alternative explicitly.

---

## 6. Important Assumptions

- Self-registration only ever creates Organizer accounts; Admin
  accounts must be seeded/provisioned separately, to avoid privilege
  escalation through the public form.
- An Organizer can only see and manage events/requests they created
  themselves; an Admin can see and manage everything. This ownership
  is tracked via an `organizer_id` foreign key on `Event`, in addition
  to the free-text `organizer` display name field used on printed/
  displayed event details.
- A resource's `buffer_minutes` (setup/teardown time) is treated as
  part of that resource's booked window when checking for conflicts.
- Cancelling an event or an allocation releases the associated
  resource(s) for the affected time window but keeps a historical
  record (status is set to `CANCELLED`, not deleted).
- Dates/times are stored and compared as naive local datetimes for
  simplicity; the app does not currently handle multiple timezones.
- No email/notification system is implemented — status changes are
  reflected only in the UI, not sent externally.

---

## Project Structure

```
app/
  __init__.py          # App factory, extensions, blueprints, error handlers
  decorators.py        # @admin_required
  models.py            # SQLAlchemy models (User, Event, Resource, ...)
  routes/
    auth.py            # login / register / logout
    dashboard.py
    events.py
    resources.py
    requests.py
    availability.py
    admin.py            # approvals (admin-only)
  services/
    booking.py          # conflict detection + atomic allocation
    suitability.py       # type/capacity checks
    alternatives.py       # alternative-resource suggestion
    status.py            # approval/rejection state transitions
  templates/             # Jinja2 + Tailwind templates
tests/                   # pytest test suite
seed.py                  # creates demo admin/organizer + sample resources
requirements.txt
```

## Running Tests

```bash
pip install -r requirements.txt
pytest -q
```
\n\n## 8. Validation checklist\n\nFor a clean local verification:\n\n```bash\npython -m compileall -q app seed.py run.py\npytest -q\n```\n\nThe test suite covers database models, conflict detection, suitability,\nmulti-resource atomic allocation, alternatives, availability, approval and\nrejection workflows, allocation cancellation, waitlist promotion, and role-based access control.\n