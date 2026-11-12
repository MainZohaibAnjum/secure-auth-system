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

