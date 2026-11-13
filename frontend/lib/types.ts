// The shapes of the JSON our FastAPI backend sends back

export type Role = "user" | "admin";

export type User = {
  id: string;
  email: string;
  role: Role;
  totp_enabled: boolean;
  created_at: string;
};


export type LoginResponse = {
  access_token: string | null;
  token_type: string;
  requires_2fa: boolean;
  challenge_token: string | null;
};

export type TwoFactorSetup = {
  secret: string;
  otpauth_uri: string;
  qr_code_data_uri: string;
};


export type DeviceSession = {
  id: string;
  user_agent: string | null;
  ip: string | null;
  signed_in_at: string;
  last_active_at: string;
  current: boolean;
};


export type TwoFactorEnableResult = User & {
  recovery_codes: string[];
};

export type RecoveryCodes = {
  recovery_codes: string[];
};

export type RecoveryCodesStatus = {
  remaining: number;
};

export type AdminUser = User & {
  is_active: boolean;
};


export type Product = {
  id: string;
  name: string;
  description: string;
  price_cents: number;
  stock: number;
  image_url: string | null;
  is_active: boolean;
  created_at: string;
};

// What the admin form sends to add or change a product
export type ProductInput = Omit<Product, "id" | "created_at">;

// One line in the cart. The server works out every amount from current prices.
export type CartLine = {
  product: Product;
  quantity: number;
  line_total_cents: number;
};

export type Cart = {
  items: CartLine[];
  total_cents: number;
};
