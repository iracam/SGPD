import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { TextareaModule } from 'primeng/textarea';
import { Observable, finalize, forkJoin } from 'rxjs';

import { FieldErrors, errorMessage, fieldErrors } from '../../core/api/api-error';
import { Papel, Permissao } from './models/papeis.models';
import { PapeisService } from './papeis.service';

@Component({
  selector: 'app-papeis-page',
  imports: [
    ReactiveFormsModule,
    ButtonModule,
    CheckboxModule,
    DialogModule,
    InputTextModule,
    MessageModule,
    TextareaModule,
  ],
  templateUrl: './papeis.html',
  styleUrl: './papeis.scss',
})
export class PapeisPage {
  private readonly service = inject(PapeisService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  readonly papeis = signal<Papel[]>([]);
  readonly permissoes = signal<Permissao[]>([]);
  readonly carregando = signal(false);
  readonly erroPagina = signal('');
  readonly vazio = computed(() => !this.carregando() && this.papeis().length === 0);

  readonly emEdicao = signal<Papel | null>(null);
  readonly dialogoAberto = signal(false);
  readonly salvando = signal(false);
  readonly erroFormulario = signal('');
  readonly errosCampo = signal<FieldErrors>({});

  readonly titulo = computed(() =>
    this.emEdicao() ? `Editar papel: ${this.emEdicao()?.code}` : 'Novo papel',
  );

  readonly formulario = this.formBuilder.nonNullable.group({
    code: ['', [Validators.required]],
    name: ['', [Validators.required]],
    description: [''],
    is_active: [true],
    permission_ids: [[] as number[]],
    reason: ['', [Validators.required]],
  });

  constructor() {
    this.carregar();
  }

  erros(campo: string): string[] {
    return this.errosCampo()[campo] ?? [];
  }

  abrir(papel?: Papel): void {
    this.emEdicao.set(papel ?? null);
    this.errosCampo.set({});
    this.erroFormulario.set('');
    this.formulario.reset({
      code: papel?.code ?? '',
      name: papel?.name ?? '',
      description: papel?.description ?? '',
      is_active: papel?.is_active ?? true,
      permission_ids: papel?.permissions.map((permissao) => permissao.id) ?? [],
      reason: '',
    });
    // O código é imutável após a criação.
    if (papel) {
      this.formulario.controls.code.disable();
    } else {
      this.formulario.controls.code.enable();
    }
    this.dialogoAberto.set(true);
  }

  salvar(): void {
    if (this.formulario.invalid || this.salvando()) {
      this.formulario.markAllAsTouched();
      return;
    }
    const valor = this.formulario.getRawValue();
    const permission_ids = valor.permission_ids;
    const papel = this.emEdicao();

    const execucao: Observable<Papel> = papel
      ? this.service.atualizar(papel.id, {
          version: papel.version,
          name: valor.name,
          description: valor.description,
          is_active: valor.is_active,
          permission_ids,
          reason: valor.reason,
        })
      : this.service.criar({
          code: valor.code,
          name: valor.name,
          description: valor.description,
          permission_ids,
          reason: valor.reason,
        });

    this.salvando.set(true);
    this.erroFormulario.set('');
    this.errosCampo.set({});
    execucao
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

  private carregar(): void {
    this.carregando.set(true);
    this.erroPagina.set('');
    forkJoin({ papeis: this.service.listar(), permissoes: this.service.permissoes() })
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: ({ papeis, permissoes }) => {
          this.papeis.set(papeis.results);
          this.permissoes.set(permissoes.results);
        },
        error: (error) => this.erroPagina.set(errorMessage(error)),
      });
  }
}
