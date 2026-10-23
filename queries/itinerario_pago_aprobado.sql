-- =============================================================================
-- Consulta: Itinerario(s) de usuario(s) con pago APROBADO, su valor y los
-- datos del usuario.
--
-- Base de datos: PostgreSQL (schema actual de Travelia).
-- Tablas: users, payments, itineraries.
-- Relación: payments.user_id -> users.id ; itineraries.user_id -> users.id
--           (no existe FK directa payments -> itineraries; se relacionan por
--            el usuario).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- CONSULTA 1: un registro por itinerario, emparejado con el ÚLTIMO pago
-- aprobado del usuario (evita duplicar filas por múltiples pagos).
-- -----------------------------------------------------------------------------
WITH approved_payments AS (
    SELECT DISTINCT ON (user_id)
        user_id,
        id              AS payment_id,
        reference,
        amount_in_cents,
        currency,
        transaction_id,
        created_at      AS paid_at
    FROM payments
    WHERE status = 'APPROVED'
    ORDER BY user_id, created_at DESC
)
SELECT
    u.id                        AS user_id,
    u.email,
    u.full_name,
    u.role,
    u.subscription_type,
    ap.payment_id,
    ap.reference,
    ap.amount_in_cents,
    ROUND(ap.amount_in_cents / 100.0, 2) AS amount,
    ap.currency,
    ap.transaction_id,
    ap.paid_at,
    i.id                        AS itinerary_id,
    i.title                     AS itinerary_title,
    i.summary,
    i.arrival_date,
    i.departure_date,
    i.total_days,
    i.is_public,
    i.created_at                AS itinerary_created_at
FROM users u
JOIN approved_payments ap ON ap.user_id = u.id
JOIN itineraries i        ON i.user_id  = u.id
-- Para un usuario específico, descomenta y reemplaza el UUID:
-- WHERE u.id = '00000000-0000-0000-0000-000000000000'
ORDER BY ap.paid_at DESC, i.created_at DESC;


-- -----------------------------------------------------------------------------
-- CONSULTA 2 (detalle completo): un registro por cada pago aprobado y cada
-- itinerario del usuario. Útil para conciliación (puede repetir el itinerario
-- si el usuario tiene más de un pago aprobado).
-- -----------------------------------------------------------------------------
SELECT
    u.id                        AS user_id,
    u.email,
    u.full_name,
    u.role,
    u.subscription_type,
    p.id                        AS payment_id,
    p.reference,
    p.status                    AS payment_status,
    p.amount_in_cents,
    ROUND(p.amount_in_cents / 100.0, 2) AS amount,
    p.currency,
    p.transaction_id,
    p.created_at                AS paid_at,
    i.id                        AS itinerary_id,
    i.title                     AS itinerary_title,
    i.summary,
    i.arrival_date,
    i.departure_date,
    i.total_days,
    i.is_public,
    i.created_at                AS itinerary_created_at
FROM users u
JOIN payments    p ON p.user_id = u.id AND p.status = 'APPROVED'
JOIN itineraries i ON i.user_id = u.id
-- WHERE u.id = '00000000-0000-0000-0000-000000000000'
ORDER BY p.created_at DESC, i.created_at DESC;
