import { DatePipe } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputNumberModule } from 'primeng/inputnumber';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { SelectModule } from 'primeng/select';
import { TextareaModule } from 'primeng/textarea';
import { Observable, finalize, forkJoin } from 'rxjs';

import { FieldErrors, errorMessage, fieldErrors } from '../../core/api/api-error';
import { Setor, TipoEscopoSetor } from '../setores/models/setores.models';
import { SetoresService } from '../setores/setores.service';
import {
  CandidatoResponsavel,
  EdicaoResponsabilidadeSetor,
  NovaResponsabilidadeSetor,
  ResponsabilidadeSetor,
} from './models/responsaveis.models';
import { ResponsaveisService } from './responsaveis.service';

@Component({
  selector: 'app-responsaveis-page',
  imports: [
    DatePipe,
    ReactiveFormsModule,
    ButtonModule,
    DialogModule,
    InputNumberModule,
    InputTextModule,
    MessageModule,
    SelectModule,
    TextareaModule,
  ],
  templateUrl: './responsaveis.html',
  styleUrl: './responsaveis.scss',
})
export class ResponsaveisPage {
  private readonly service = inject(ResponsaveisService);
  private readonly setoresService = inject(SetoresService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  readonly responsabilidades = signal<ResponsabilidadeSetor[]>([]);
  readonly candidatos = signal<CandidatoResponsavel[]>([]);
  readonly setores = signal<Setor[]>([]);
  readonly setoresAtivos = computed(() => this.setores().filter((setor) => setor.is_active));
  readonly carregando = signal(false);
  readonly erroPagina = signal('');
  readonly vazio = computed(
    () => !this.carregando() && this.responsabilidades().length === 0,
  );

  readonly selecionada = signal<ResponsabilidadeSetor | null>(null);
  readonly dialogoAberto = signal(false);
  readonly salvando = signal(false);
  readonly erroFormulario = signal('');
  readonly errosCampo = signal<FieldErrors>({});
  readonly reativando = computed(
    () => this.selecionada() !== null && !this.selecionada()?.is_active,
  );
  readonly titulo = computed(() => {
    const responsibility = this.selecionada();
    if (!responsibility) {
      return 'Novo responsável por setor';
    }
    return responsibility.is_active
      ? `Editar responsabilidade: ${responsibility.user.display_name}`
      : `Reativar responsabilidade: ${responsibility.user.display_name}`;
  });

  readonly revogando = signal<ResponsabilidadeSetor | null>(null);
  readonly dialogoRevogacaoAberto = signal(false);
  readonly revogandoAgora = signal(false);
  readonly erroRevogacao = signal('');

  readonly tiposEscopo: { label: string; value: TipoEscopoSetor }[] = [
    { label: 'Todas as empresas', value: 'GLOBAL' },
    { label: 'Empresa', value: 'COMPANY' },
    { label: 'Filial', value: 'BRANCH' },
  ];

  readonly formulario = this.formBuilder.group({
    sector_id: this.formBuilder.control<number | null>(null, Validators.required),
    user_id: this.formBuilder.control<number | null>(null, Validators.required),
    scope_type: this.formBuilder.nonNullable.control<TipoEscopoSetor>('GLOBAL'),
    company_code: this.formBuilder.control<number | null>(null),
    branch_code: this.formBuilder.control<number | null>(null),
    valid_from: this.formBuilder.nonNullable.control(
      this.dataHoraLocal(new Date()),
      Validators.required,
    ),
    valid_until: this.formBuilder.control<string | null>(null),
    reason: this.formBuilder.nonNullable.control('', Validators.required),
  });

  readonly formularioRevogacao = this.formBuilder.group({
    reason: this.formBuilder.nonNullable.control('', Validators.required),
  });

  constructor() {
    this.configurarValidacaoEscopo('GLOBAL');
    this.carregar();
  }

  erros(campo: string): string[] {
    return this.errosCampo()[campo] ?? [];
  }

  abrir(responsibility?: ResponsabilidadeSetor): void {
    this.selecionada.set(responsibility ?? null);
    this.erroFormulario.set('');
    this.errosCampo.set({});
    this.habilitarIdentidade();
    this.formulario.patchValue({
      sector_id: responsibility?.sector.id ?? null,
      user_id: responsibility?.user.id ?? null,
      scope_type: responsibility?.scope_type ?? 'GLOBAL',
      company_code: responsibility?.company_code ?? null,
      branch_code: responsibility?.branch_code ?? null,
      valid_from: responsibility
        ? this.dataHoraLocal(new Date(responsibility.valid_from))
        : this.dataHoraLocal(new Date()),
      valid_until: responsibility?.valid_until
        ? this.dataHoraLocal(new Date(responsibility.valid_until))
        : null,
      reason: '',
    });
    this.configurarValidacaoEscopo(responsibility?.scope_type ?? 'GLOBAL');
    if (responsibility) {
      this.desabilitarIdentidade();
    }
    this.dialogoAberto.set(true);
  }

  alterarTipoEscopo(): void {
    const scopeType = this.formulario.controls.scope_type.value;
    this.formulario.patchValue({
      company_code: null,
      branch_code: null,
    });
    this.configurarValidacaoEscopo(scopeType);
  }

  abrirRevogacao(responsibility: ResponsabilidadeSetor): void {
    this.revogando.set(responsibility);
    this.formularioRevogacao.reset({ reason: '' });
    this.erroRevogacao.set('');
    this.dialogoRevogacaoAberto.set(true);
  }

  rotuloEscopo(responsibility: ResponsabilidadeSetor): string {
    if (responsibility.scope_type === 'GLOBAL') {
      return 'Todas as empresas';
    }
    if (responsibility.scope_type === 'COMPANY') {
      return `Empresa ${responsibility.company_code}`;
    }
    return `Empresa ${responsibility.company_code} · Filial ${responsibility.branch_code}`;
  }

  rotuloSituacao(responsibility: ResponsabilidadeSetor): string {
    if (!responsibility.is_active) {
      return 'Revogado';
    }
    if (responsibility.is_effective) {
      return 'Vigente';
    }
    return new Date(responsibility.valid_from).getTime() > Date.now()
      ? 'Agendado'
      : 'Expirado';
  }

  salvar(): void {
    if (this.formulario.invalid || this.salvando()) {
      this.formulario.markAllAsTouched();
      return;
    }
    const value = this.formulario.getRawValue();
    const selected = this.selecionada();
    let operation: Observable<ResponsabilidadeSetor>;
    if (selected?.is_active) {
      operation = this.service.atualizar(selected.id, {
        version: selected.version,
        valid_from: value.valid_from,
        valid_until: value.valid_until || null,
        reason: value.reason,
      } satisfies EdicaoResponsabilidadeSetor);
    } else {
      operation = this.service.associar({
        sector_id: value.sector_id as number,
        user_id: value.user_id as number,
        scope_type: value.scope_type,
        company_code: value.scope_type === 'GLOBAL' ? null : value.company_code,
        branch_code: value.scope_type === 'BRANCH' ? value.branch_code : null,
        valid_from: value.valid_from,
        valid_until: value.valid_until || null,
        reason: value.reason,
      } satisfies NovaResponsabilidadeSetor);
    }

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

  revogar(): void {
    const responsibility = this.revogando();
    if (
      !responsibility ||
      this.formularioRevogacao.invalid ||
      this.revogandoAgora()
    ) {
      this.formularioRevogacao.markAllAsTouched();
      return;
    }
    this.revogandoAgora.set(true);
    this.erroRevogacao.set('');
    this.service
      .revogar(responsibility.id, {
        version: responsibility.version,
        reason: this.formularioRevogacao.controls.reason.value,
      })
      .pipe(
        finalize(() => this.revogandoAgora.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () => {
          this.dialogoRevogacaoAberto.set(false);
          this.carregar();
        },
        error: (error) => this.erroRevogacao.set(errorMessage(error)),
      });
  }

  private habilitarIdentidade(): void {
    this.formulario.controls.sector_id.enable();
    this.formulario.controls.user_id.enable();
    this.formulario.controls.scope_type.enable();
  }

  private desabilitarIdentidade(): void {
    this.formulario.controls.sector_id.disable();
    this.formulario.controls.user_id.disable();
    this.formulario.controls.scope_type.disable();
    this.formulario.controls.company_code.disable();
    this.formulario.controls.branch_code.disable();
  }

  private configurarValidacaoEscopo(scopeType: TipoEscopoSetor): void {
    const company = this.formulario.controls.company_code;
    const branch = this.formulario.controls.branch_code;
    company.clearValidators();
    branch.clearValidators();
    if (scopeType === 'GLOBAL') {
      company.disable();
      branch.disable();
    } else {
      company.enable();
      company.addValidators([Validators.required, Validators.min(1)]);
      if (scopeType === 'BRANCH') {
        branch.enable();
        branch.addValidators([Validators.required, Validators.min(1)]);
      } else {
        branch.disable();
      }
    }
    company.updateValueAndValidity();
    branch.updateValueAndValidity();
  }

  private dataHoraLocal(date: Date): string {
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
    return local.toISOString().slice(0, 16);
  }

  private carregar(): void {
    this.carregando.set(true);
    this.erroPagina.set('');
    forkJoin({
      responsibilities: this.service.listar(),
      candidates: this.service.listarCandidatos(),
      sectors: this.setoresService.listar(),
    })
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: ({ responsibilities, candidates, sectors }) => {
          this.responsabilidades.set(responsibilities.results);
          this.candidatos.set(candidates.results);
          this.setores.set(sectors.results);
        },
        error: (error) => this.erroPagina.set(errorMessage(error)),
      });
  }
}
