export interface Permissao {
  id: number;
  codename: string;
  name: string;
}

export interface Papel {
  id: number;
  code: string;
  name: string;
  description: string;
  is_active: boolean;
  version: number;
  permissions: Permissao[];
}
