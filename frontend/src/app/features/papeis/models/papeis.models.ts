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

export interface NovoPapel {
  code: string;
  name: string;
  description: string;
  permission_ids: number[];
  reason: string;
}

export interface EdicaoPapel {
  version: number;
  name: string;
  description: string;
  is_active: boolean;
  permission_ids: number[];
  reason: string;
}
