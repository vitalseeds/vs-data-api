-- Requires packeting_batches.seed_lot_fk
-- to be changed from text to number in fm
SELECT
    B.awaiting_upload,
    B.batch_number,
    B.packets,
    B.to_pack,
    L.seed_lot_id
FROM
    "packeting_batches" B -- LEFT JOIN "seed_lots" L ON B.seed_lot_fk = L.seed_lot_id
    LEFT JOIN "seed_lots" L ON B.seed_lot_fk = L.seed_lot_id
WHERE
    awaiting_upload = 'yes'