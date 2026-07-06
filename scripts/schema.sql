CREATE SEQUENCE IF NOT EXISTS seq_product_variant START 1;

CREATE TABLE IF NOT EXISTS products (
  product_id UUID PRIMARY KEY DEFAULT uuid(),
  name TEXT NOT NULL,
  description TEXT,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
  updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS product_variants (
  variant_id UUID PRIMARY KEY DEFAULT uuid(),
  product_id UUID NOT NULL,
  sku TEXT NOT NULL UNIQUE,
  color TEXT,
  size TEXT,
  other_attributes JSON,
  default_price DECIMAL(18, 2) NOT NULL DEFAULT 0,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
  updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
  FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS suppliers (
  supplier_id UUID PRIMARY KEY DEFAULT uuid(),
  name TEXT NOT NULL UNIQUE,
  notes TEXT,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS payment_methods (
  payment_method_id UUID PRIMARY KEY DEFAULT uuid(),
  name TEXT NOT NULL UNIQUE,
  affects_cash BOOLEAN NOT NULL DEFAULT TRUE,
  active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS expense_categories (
  expense_category_id UUID PRIMARY KEY DEFAULT uuid(),
  name TEXT NOT NULL UNIQUE,
  active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS purchases (
  purchase_id UUID PRIMARY KEY DEFAULT uuid(),
  purchase_date DATE NOT NULL,
  supplier_id UUID,
  payment_method_id UUID,
  invoice_number TEXT,
  subtotal DECIMAL(18, 2) NOT NULL DEFAULT 0,
  direct_cost_total DECIMAL(18, 2) NOT NULL DEFAULT 0,
  total DECIMAL(18, 2) NOT NULL DEFAULT 0,
  notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
  FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
  FOREIGN KEY (payment_method_id) REFERENCES payment_methods(payment_method_id)
);

CREATE TABLE IF NOT EXISTS purchase_lines (
  purchase_line_id UUID PRIMARY KEY DEFAULT uuid(),
  purchase_id UUID NOT NULL,
  variant_id UUID NOT NULL,
  supplier_item_name TEXT,
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  unit_cost DECIMAL(18, 2) NOT NULL CHECK (unit_cost >= 0),
  allocated_direct_cost DECIMAL(18, 2) NOT NULL DEFAULT 0,
  effective_unit_cost DECIMAL(18, 2) NOT NULL DEFAULT 0,
  line_total DECIMAL(18, 2) NOT NULL DEFAULT 0,
  FOREIGN KEY (purchase_id) REFERENCES purchases(purchase_id),
  FOREIGN KEY (variant_id) REFERENCES product_variants(variant_id)
);

CREATE TABLE IF NOT EXISTS expenses (
  expense_id UUID PRIMARY KEY DEFAULT uuid(),
  expense_date DATE NOT NULL,
  expense_category_id UUID NOT NULL,
  supplier_id UUID,
  payment_method_id UUID,
  description TEXT NOT NULL,
  amount DECIMAL(18, 2) NOT NULL CHECK (amount >= 0),
  document_path TEXT,
  notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
  FOREIGN KEY (expense_category_id) REFERENCES expense_categories(expense_category_id),
  FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
  FOREIGN KEY (payment_method_id) REFERENCES payment_methods(payment_method_id)
);

CREATE TABLE IF NOT EXISTS sales (
  sale_id UUID PRIMARY KEY DEFAULT uuid(),
  sale_date TIMESTAMP NOT NULL,
  source TEXT NOT NULL DEFAULT 'manual',
  customer_name TEXT,
  status TEXT NOT NULL DEFAULT 'confirmed',
  gross_amount DECIMAL(18, 2) NOT NULL DEFAULT 0,
  discount_amount DECIMAL(18, 2) NOT NULL DEFAULT 0,
  net_amount DECIMAL(18, 2) NOT NULL DEFAULT 0,
  notes TEXT,
  mobile_sale_uid TEXT UNIQUE,
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS sale_lines (
  sale_line_id UUID PRIMARY KEY DEFAULT uuid(),
  sale_id UUID NOT NULL,
  variant_id UUID NOT NULL,
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  unit_price DECIMAL(18, 2) NOT NULL CHECK (unit_price >= 0),
  discount_amount DECIMAL(18, 2) NOT NULL DEFAULT 0,
  line_total DECIMAL(18, 2) NOT NULL DEFAULT 0,
  cogs_amount DECIMAL(18, 2) NOT NULL DEFAULT 0,
  margin_amount DECIMAL(18, 2) NOT NULL DEFAULT 0,
  FOREIGN KEY (sale_id) REFERENCES sales(sale_id),
  FOREIGN KEY (variant_id) REFERENCES product_variants(variant_id)
);

CREATE TABLE IF NOT EXISTS sale_payments (
  sale_payment_id UUID PRIMARY KEY DEFAULT uuid(),
  sale_id UUID NOT NULL,
  payment_method_id UUID NOT NULL,
  amount DECIMAL(18, 2) NOT NULL CHECK (amount >= 0),
  payment_date TIMESTAMP NOT NULL DEFAULT current_timestamp,
  notes TEXT,
  FOREIGN KEY (sale_id) REFERENCES sales(sale_id),
  FOREIGN KEY (payment_method_id) REFERENCES payment_methods(payment_method_id)
);

CREATE TABLE IF NOT EXISTS stock_movements (
  stock_movement_id UUID PRIMARY KEY DEFAULT uuid(),
  movement_date TIMESTAMP NOT NULL DEFAULT current_timestamp,
  variant_id UUID NOT NULL,
  movement_type TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  reference_table TEXT,
  reference_id UUID,
  external_ref TEXT,
  reason TEXT,
  notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
  FOREIGN KEY (variant_id) REFERENCES product_variants(variant_id)
);

ALTER TABLE stock_movements ADD COLUMN IF NOT EXISTS external_ref TEXT;

CREATE TABLE IF NOT EXISTS reservations (
  reservation_id UUID PRIMARY KEY DEFAULT uuid(),
  variant_id UUID NOT NULL,
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  reserved_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
  status TEXT NOT NULL DEFAULT 'active',
  notes TEXT,
  FOREIGN KEY (variant_id) REFERENCES product_variants(variant_id)
);

CREATE TABLE IF NOT EXISTS inventory_lots (
  lot_id UUID PRIMARY KEY DEFAULT uuid(),
  variant_id UUID NOT NULL,
  purchase_line_id UUID,
  external_ref TEXT,
  received_date DATE NOT NULL,
  original_quantity INTEGER NOT NULL CHECK (original_quantity >= 0),
  remaining_quantity INTEGER NOT NULL CHECK (remaining_quantity >= 0),
  unit_cost DECIMAL(18, 2) NOT NULL CHECK (unit_cost >= 0),
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
  FOREIGN KEY (variant_id) REFERENCES product_variants(variant_id),
  FOREIGN KEY (purchase_line_id) REFERENCES purchase_lines(purchase_line_id)
);

ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS external_ref TEXT;

CREATE TABLE IF NOT EXISTS inventory_allocations (
  allocation_id UUID PRIMARY KEY DEFAULT uuid(),
  sale_line_id UUID NOT NULL,
  lot_id UUID NOT NULL,
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  unit_cost DECIMAL(18, 2) NOT NULL CHECK (unit_cost >= 0),
  total_cost DECIMAL(18, 2) NOT NULL CHECK (total_cost >= 0),
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
  FOREIGN KEY (sale_line_id) REFERENCES sale_lines(sale_line_id),
  FOREIGN KEY (lot_id) REFERENCES inventory_lots(lot_id)
);

CREATE TABLE IF NOT EXISTS cash_movements (
  cash_movement_id UUID PRIMARY KEY DEFAULT uuid(),
  movement_date TIMESTAMP NOT NULL DEFAULT current_timestamp,
  payment_method_id UUID NOT NULL,
  movement_type TEXT NOT NULL,
  amount DECIMAL(18, 2) NOT NULL,
  reference_table TEXT,
  reference_id UUID,
  notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
  FOREIGN KEY (payment_method_id) REFERENCES payment_methods(payment_method_id)
);

CREATE TABLE IF NOT EXISTS documents (
  document_id UUID PRIMARY KEY DEFAULT uuid(),
  document_type TEXT NOT NULL,
  original_path TEXT NOT NULL,
  supplier_id UUID,
  document_date DATE,
  total_amount DECIMAL(18, 2),
  status TEXT NOT NULL DEFAULT 'pending_review',
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
  FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

CREATE TABLE IF NOT EXISTS supplier_product_aliases (
  alias_id UUID PRIMARY KEY DEFAULT uuid(),
  supplier_id UUID,
  supplier_item_name TEXT NOT NULL,
  variant_id UUID NOT NULL,
  confidence TEXT NOT NULL DEFAULT 'manual',
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
  FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
  FOREIGN KEY (variant_id) REFERENCES product_variants(variant_id)
);

CREATE TABLE IF NOT EXISTS import_batches (
  import_batch_id UUID PRIMARY KEY DEFAULT uuid(),
  source TEXT NOT NULL,
  source_path TEXT,
  status TEXT NOT NULL DEFAULT 'pending_review',
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
  reviewed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
  audit_id UUID PRIMARY KEY DEFAULT uuid(),
  event_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
  entity_table TEXT NOT NULL,
  entity_id UUID,
  action TEXT NOT NULL,
  details JSON
);

CREATE OR REPLACE VIEW v_stock_current AS
WITH movements AS (
  SELECT
    variant_id,
    SUM(quantity) AS physical_stock
  FROM stock_movements
  GROUP BY variant_id
),
reserved AS (
  SELECT
    variant_id,
    SUM(quantity) AS reserved_stock
  FROM reservations
  WHERE status = 'active'
  GROUP BY variant_id
)
SELECT
  pv.variant_id,
  pv.sku,
  p.name AS product_name,
  pv.color,
  pv.size,
  pv.default_price,
  COALESCE(m.physical_stock, 0) AS physical_stock,
  COALESCE(r.reserved_stock, 0) AS reserved_stock,
  COALESCE(m.physical_stock, 0) - COALESCE(r.reserved_stock, 0) AS available_stock
FROM product_variants pv
JOIN products p ON p.product_id = pv.product_id
LEFT JOIN movements m ON m.variant_id = pv.variant_id
LEFT JOIN reserved r ON r.variant_id = pv.variant_id
WHERE pv.active = TRUE AND p.active = TRUE;

INSERT INTO payment_methods (name)
SELECT value
FROM (VALUES ('Efectivo'), ('Transferencia'), ('Mercado Pago'), ('Tarjeta'), ('Otro')) AS t(value)
WHERE NOT EXISTS (
  SELECT 1 FROM payment_methods pm WHERE pm.name = t.value
);

INSERT INTO expense_categories (name)
SELECT value
FROM (VALUES ('Packaging'), ('Publicidad'), ('Envios'), ('Otros')) AS t(value)
WHERE NOT EXISTS (
  SELECT 1 FROM expense_categories ec WHERE ec.name = t.value
);
