import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  FormBuilder,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { DialogModule } from 'primeng/dialog';
import { InputNumberModule } from 'primeng/inputnumber';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { SelectModule } from 'primeng/select';
import { TextareaModule } from 'primeng/textarea';
import { Observable, finalize, forkJoin } from 'rxjs';

import { FieldErrors, errorMessage, fieldErrors } from '../../core/api/api-error';
import {
  EdicaoSetor,
  EscopoSetorEntrada,
  NovoSetor,
  ResponsavelSetorEntrada,
  Setor,
  TipoEscopoSetor,
  UsuarioResponsavelCandidato,
} from './models/setores.models';
import { SetoresService } from './setores.service';

type EscopoForm = FormGroup<{
  scope_type: FormControl<TipoEscopoSetor>;
  company_code: FormControl<number | null>;
  branch_code: FormControl<number | null>;
}>;

type ResponsavelForm = FormGroup<{
  user_id: FormControl<number | null>;
  valid_from: FormControl<string>;
  valid_until: FormControl<string>;
}>;

@Component({
  selector: 'app-setores-page',
  imports: [
    ReactiveFormsModule,
    ButtonModule,
    CheckboxModule,
    DialogModule,
    InputNumberModule,
    InputTextModule,
    MessageModule,
    SelectModule,
    TextareaModule,
  ],
  templateUrl: './setores.html',
  styleUrl: './setores.scss',
})
export class SetoresPage {
  private readonly service = inject(SetoresService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  readonly setores = signal<Setor[]>([]);
  readonly candidatos = signal<UsuarioResponsavelCandidato[]>([]);
  readonly carregando = signal(false);
  readonly erroPagina = signal('');
  readonly vazio = computed(() => !this.carregando() && this.setores().length === 0);

  readonly emEdicao = signal<Setor | null>(null);
  readonly dialogoAberto = signal(false);
  readonly salvando = signal(false);
  readonly erroFormulario = signal('');
  readonly errosCampo = signal<FieldErrors>({});

  readonly tiposEscopo: { label: string; value: TipoEscopoSetor }[] = [
    { label: 'Todas as empresas', value: 'GLOBAL' },
    { label: 'Empresa', value: 'COMPANY' },
    { label: 'Filial', value: 'BRANCH' },
  ];

  readonly titulo = computed(() =>
    this.emEdicao() ? `Editar setor: ${this.emEdicao()?.code}` : 'Novo setor',
  );
  readonly setoresEscalada = computed(() =>
    this.setores().filter(
      (setor) => setor.is_active && setor.id !== this.emEdicao()?.id,
    ),
  );

  readonly formulario = this.formBuilder.group({
    code: this.formBuilder.nonNullable.control('', Validators.required),
    name: this.formBuilder.nonNullable.control('', Validators.required),
    description: this.formBuilder.nonNullable.control(''),
    default_due_hours: this.formBuilder.nonNullable.control(24, [
      Validators.required,
      Validators.min(1),
      Validators.max(8760),
    ]),
    blocks_process: this.formBuilder.nonNullable.control(true),
    allows_amount: this.formBuilder.nonNullable.control(false),
    requires_evidence: this.formBuilder.nonNullable.control(false),
    escalation_sector_id: this.formBuilder.control<number | null>(null),
    is_active: this.formBuilder.nonNullable.control(true),
    scopes: this.formBuilder.array([this.criarEscopo('GLOBAL')], Validators.minLength(1)),
    responsibles: this.formBuilder.array<ResponsavelForm>([]),
  });

  constructor() {
    this.carregar();
  }

  erros(campo: string): string[] {
    return this.errosCampo()[campo] ?? [];
  }

  errosEscopo(index: number, campo: string): string[] {
    return this.erros(`scopes.${index}.${campo}`);
  }

  abrir(setor?: Setor): void {
    this.emEdicao.set(setor ?? null);
    this.errosCampo.set({});
    this.erroFormulario.set('');
    this.formulario.patchValue({
      code: setor?.code ?? '',
      name: setor?.name ?? '',
      description: setor?.description ?? '',
      default_due_hours: setor?.default_due_hours ?? 24,
      blocks_process: setor?.blocks_process ?? true,
      allows_amount: setor?.allows_amount ?? false,
      requires_evidence: setor?.requires_evidence ?? false,
      escalation_sector_id: setor?.escalation_sector?.id ?? null,
      is_active: setor?.is_active ?? true,
    });
    this.formulario.controls.scopes.clear();
    for (const current of setor?.scopes ?? [
      { scope_type: 'GLOBAL' as const, company_code: null, branch_code: null },
    ]) {
      this.formulario.controls.scopes.push(
        this.criarEscopo(
          current.scope_type,
          current.company_code,
          current.branch_code,
        ),
      );
    }
    this.formulario.controls.responsibles.clear();
    for (const current of setor?.responsibles ?? []) {
      this.formulario.controls.responsibles.push(
        this.criarResponsavel(
          current.user.id,
          this.paraDataHoraLocal(current.valid_from),
          this.paraDataHoraLocal(current.valid_until),
        ),
      );
    }
    if (setor) {
      this.formulario.controls.code.disable();
    } else {
      this.formulario.controls.code.enable();
    }
    this.dialogoAberto.set(true);
  }

  adicionarEscopo(): void {
    this.formulario.controls.scopes.push(this.criarEscopo('COMPANY'));
  }

  removerEscopo(index: number): void {
    if (this.formulario.controls.scopes.length > 1) {
      this.formulario.controls.scopes.removeAt(index);
    }
  }

  adicionarResponsavel(): void {
    this.formulario.controls.responsibles.push(this.criarResponsavel());
  }

  removerResponsavel(index: number): void {
    this.formulario.controls.responsibles.removeAt(index);
  }

  errosResponsavel(index: number, campo: string): string[] {
    return this.erros(`responsibles.${index}.${campo}`);
  }

  alterarTipoEscopo(index: number): void {
    const current = this.formulario.controls.scopes.at(index);
    const type = current.controls.scope_type.value;
    if (type === 'GLOBAL') {
      this.formulario.controls.scopes.clear();
      this.formulario.controls.scopes.push(this.criarEscopo('GLOBAL'));
      return;
    }
    current.controls.company_code.setValue(null);
    current.controls.branch_code.setValue(null);
    this.configurarValidacaoEscopo(current, type);
  }

  possuiEscopoGlobal(): boolean {
    return this.formulario.controls.scopes.controls.some(
      (control) => control.controls.scope_type.value === 'GLOBAL',
    );
  }

  rotuloEscopo(scope: Setor['scopes'][number]): string {
    if (scope.scope_type === 'GLOBAL') {
      return 'Todas as empresas';
    }
    if (scope.scope_type === 'COMPANY') {
      return `Empresa ${scope.company_code}`;
    }
    return `Empresa ${scope.company_code} · Filial ${scope.branch_code}`;
  }

  salvar(): void {
    if (this.formulario.invalid || this.salvando()) {
      this.formulario.markAllAsTouched();
      return;
    }
    const value = this.formulario.getRawValue();
    const scopes: EscopoSetorEntrada[] = value.scopes.map((scope) => ({
      scope_type: scope.scope_type,
      company_code: scope.scope_type === 'GLOBAL' ? null : scope.company_code,
      branch_code: scope.scope_type === 'BRANCH' ? scope.branch_code : null,
    }));
    const responsibles: ResponsavelSetorEntrada[] = value.responsibles.map(
      (responsible) => ({
        user_id: responsible.user_id as number,
        ...(responsible.valid_from ? { valid_from: responsible.valid_from } : {}),
        valid_until: responsible.valid_until || null,
      }),
    );
    const common = {
      name: value.name,
      description: value.description,
      default_due_hours: value.default_due_hours,
      blocks_process: value.blocks_process,
      allows_amount: value.allows_amount,
      requires_evidence: value.requires_evidence,
      escalation_sector_id: value.escalation_sector_id,
      scopes,
      responsibles,
    };
    const sector = this.emEdicao();
    const operation: Observable<Setor> = sector
      ? this.service.atualizar(sector.id, {
          ...common,
          version: sector.version,
          is_active: value.is_active,
        } satisfies EdicaoSetor)
      : this.service.criar({
          ...common,
          code: value.code,
        } satisfies NovoSetor);

    this.salvando.set(true);
    this.erroFormulario.set('');
    this.errosCampo.set({});
    operation
      .pipe(
        finalize(() => this.salvando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () => {
          this.dialogoAberto.set(false);
          this.carregar();
        },
        error: (error) => {
          this.errosCampo.set(fieldErrors(error));
          this.erroFormulario.set(errorMessage(error));
        },
      });
  }

  private criarEscopo(
    scopeType: TipoEscopoSetor,
    companyCode: number | null = null,
    branchCode: number | null = null,
  ): EscopoForm {
    const group = this.formBuilder.group({
      scope_type: this.formBuilder.nonNullable.control<TipoEscopoSetor>(scopeType),
      company_code: this.formBuilder.control<number | null>(companyCode),
      branch_code: this.formBuilder.control<number | null>(branchCode),
    });
    this.configurarValidacaoEscopo(group, scopeType);
    return group;
  }

  private criarResponsavel(
    userId: number | null = null,
    validFrom = '',
    validUntil = '',
  ): ResponsavelForm {
    return this.formBuilder.group({
      user_id: this.formBuilder.control<number | null>(userId, Validators.required),
      valid_from: this.formBuilder.nonNullable.control(validFrom),
      valid_until: this.formBuilder.nonNullable.control(validUntil),
    });
  }

  private paraDataHoraLocal(value: string | null): string {
    if (!value) {
      return '';
    }
    const date = new Date(value);
    const offset = date.getTimezoneOffset() * 60_000;
    return new Date(date.getTime() - offset).toISOString().slice(0, 16);
  }

  private configurarValidacaoEscopo(
    group: EscopoForm,
    scopeType: TipoEscopoSetor,
  ): void {
    group.controls.company_code.clearValidators();
    group.controls.branch_code.clearValidators();
    if (scopeType === 'GLOBAL') {
      group.controls.company_code.disable();
      group.controls.branch_code.disable();
    } else {
      group.controls.company_code.enable();
      group.controls.company_code.addValidators([Validators.required, Validators.min(1)]);
      if (scopeType === 'BRANCH') {
        group.controls.branch_code.enable();
        group.controls.branch_code.addValidators([Validators.required, Validators.min(1)]);
      } else {
        group.controls.branch_code.disable();
      }
    }
    group.controls.company_code.updateValueAndValidity();
    group.controls.branch_code.updateValueAndValidity();
  }

  private carregar(): void {
    this.carregando.set(true);
    this.erroPagina.set('');
    forkJoin({
      setores: this.service.listar(),
      candidatos: this.service.listarCandidatos(),
    })
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: ({ setores, candidatos }) => {
          this.setores.set(setores.results);
          this.candidatos.set(candidatos.results);
        },
        error: (error) => this.erroPagina.set(errorMessage(error)),
      });
  }
}
