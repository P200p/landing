-- loans
CREATE TABLE loans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text,
  amount numeric,
  created_at timestamptz DEFAULT now(),
  status text DEFAULT 'pending',
  interest numeric DEFAULT 0
);

-- payments
CREATE TABLE payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  loan_id uuid,
  user_id text,
  paid_at timestamptz DEFAULT now(),
  amount numeric
);