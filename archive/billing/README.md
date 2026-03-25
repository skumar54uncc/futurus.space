# Archived billing & monetization

This folder holds the previous **Stripe subscriptions**, **plan tiers**, **credits**, and **billing UI** removed when the app was switched to **open access** (sign up and run simulations without payment or tier limits).

To restore monetization later:

1. Copy the Python modules back under `backend/` and re-wire `main.py` (Stripe init + `billing` router).
2. Restore `backend/schemas/billing.py` and Stripe-related settings in `core/config.py`.
3. Restore the frontend billing route, components, and `useCredits` as needed.
4. Re-add `stripe` to `backend/requirements.txt` and `stripe` / `@stripe/stripe-js` to the frontend `package.json` if you use client checkout.

Simulation limits for all users now come from **`simulation_limits`** in `backend/core/config.py` (single cap, no tiers).
