# Khan Parcel — API & Realtime Catalog

## 1. Authentication (`/api/v1/auth/`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/otp/request/` | Send 6-digit OTP code to phone number |
| `POST` | `/api/v1/auth/otp/verify/` | Verify OTP and return JWT access/refresh tokens |
| `POST` | `/api/v1/auth/token/refresh/` | Refresh expired access token |
| `POST` | `/api/v1/auth/staff/login/` | Email + password + TOTP 2FA login for staff |
| `GET/PUT` | `/api/v1/auth/profile/` | Current user profile |
| `POST` | `/api/v1/auth/devices/register/` | Register FCM push notification token |
| `POST` | `/api/v1/auth/2fa/setup/` | Generate TOTP QR secret for staff |

## 2. Riders & KYC (`/api/v1/riders/`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/riders/me/` | Current rider profile & operational stats |
| `POST` | `/api/v1/riders/onboard/` | Submit vehicle & CNIC KYC onboarding |
| `POST` | `/api/v1/riders/documents/upload/`| Upload CNIC / License document images |
| `POST` | `/api/v1/riders/status/toggle/` | Go online (AVAILABLE) / offline |
| `POST` | `/api/v1/riders/location/` | High-frequency GPS telemetry ping |
| `POST` | `/api/v1/riders/admin/documents/<id>/review/` | Staff approve/reject driver KYC |

## 3. Pricing & Quotes (`/api/v1/pricing/`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/pricing/quote/` | Calculate route distance, duration, surge & price |
| `GET` | `/api/v1/pricing/quote/<id>/` | Fetch quote details |
| `POST` | `/api/v1/pricing/promo/validate/` | Check promo code discount validity |
| `GET` | `/api/v1/pricing/rules/` | View base tariffs per vehicle type |

## 4. Delivery Orders (`/api/v1/orders/`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/orders/` | List orders (filtered by user role) |
| `POST` | `/api/v1/orders/` | Create delivery order from accepted quote |
| `GET` | `/api/v1/orders/<id>/` | Order lifecycle details & status logs |
| `POST` | `/api/v1/orders/<id>/arrived-pickup/` | Rider signals arrived at pickup |
| `POST` | `/api/v1/orders/<id>/verify-pickup/` | Verify 4-digit pickup OTP & photo |
| `POST` | `/api/v1/orders/<id>/arrived-delivery/` | Rider signals arrived at destination |
| `POST` | `/api/v1/orders/<id>/verify-delivery/` | Verify delivery OTP, recipient signature & complete |
| `POST` | `/api/v1/orders/<id>/cancel/` | Cancel order with reason |
| `POST` | `/api/v1/orders/<id>/rate/` | Customer submits 1-5 star review |

## 5. Dispatch Engine (`/api/v1/dispatch/`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/dispatch/offers/` | Rider's active pending delivery job offers |
| `POST` | `/api/v1/dispatch/offers/<id>/accept/` | Rider accepts offer |
| `POST` | `/api/v1/dispatch/offers/<id>/reject/` | Rider rejects offer |
| `POST` | `/api/v1/dispatch/manual-assign/` | Dispatcher overrides and assigns rider |

## 6. Financials & Payments (`/api/v1/payments/`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/payments/wallet/` | Current user wallet balance |
| `POST` | `/api/v1/payments/wallet/topup/` | Add funds to wallet |
| `GET` | `/api/v1/payments/wallet/statement/` | Double-entry financial statement |
| `POST` | `/api/v1/payments/payouts/` | Rider request withdrawal |
| `POST` | `/api/v1/payments/cod/remit/` | Rider submits bank deposit slip for COD cash |
| `POST` | `/api/v1/payments/admin/cod/<id>/verify/` | Staff verify and clear rider COD |

## 7. Realtime WebSocket Endpoints
- `ws://host/ws/tracking/<order_id>/?token=<jwt>`: Customer live tracking stream
- `ws://host/ws/public/tracking/<token>/`: Anonymous public tracking link stream
- `ws://host/ws/dispatcher/?token=<jwt>`: Control room dispatcher stream
- `ws://host/ws/rider/?token=<jwt>`: Rider private job offers & telemetry stream
- `ws://host/ws/chat/<order_id>/?token=<jwt>`: Realtime order in-app messaging
