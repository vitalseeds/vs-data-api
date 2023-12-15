SELECT
    B.awaiting_upload,
    "batch_number",
    "packets",
    "to_pack"
FROM
    "packeting_batches" B
WHERE
    awaiting_upload = 'yes'