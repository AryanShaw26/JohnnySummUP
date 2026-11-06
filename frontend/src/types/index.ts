export interface User {
  id: string;
  full_name: string;
  email: string;
}

export interface AuthPayload {
  email: string;
  password: string;
}

export interface RegisterPayload extends AuthPayload {
  full_name: string;
}
