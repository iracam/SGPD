import { DatePipe } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { MultiSelectModule } from 'primeng/multiselect';
import { finalize } from 'rxjs';

import { errorMessage } from '../../core/api/api-error';
import { ContextoRascunho } from './models/processo-rascunho.models';
import { ProcessoRascunhoService } from './processo-rascunho.service';

@Component({
  selector: 'app-processo-rascunho-page',
  imports: [
    DatePipe,
    ReactiveFormsModule,
    ButtonModule,
    MessageModule,
    MultiSelectModule,
  ],
  templateUrl: './processo-rascunho.html',
  styleUrl: './processo-rascunho.scss',
})
export class ProcessoRascunhoPage {
  private readonly service = inject(ProcessoRascunhoService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly formBuilder = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);
  private readonly uuid = this.route.snapshot.paramMap.get('uuid') ?? '';

  readonly contexto = signal<ContextoRascunho | null>(null);
  readonly carregando = signal(true);
  readonly salvando = signal(false);
  readonly iniciando = signal(false);
  readonly selecaoAlterada = signal(false);
  readonly erro = signal('');
  readonly aviso = signal('');
  readonly excluindo = signal(false);
  /** Só depois de confirmar o rascunho some — um clique não apaga nada. */
  readonly confirmandoExclusao = signal(false);
  readonly motivoExclusao = signal('');
  private readonly chaveInicio = signal(this.criarChaveIdempotencia());
  readonly formulario = this.formBuilder.group({
    group_version_ids: this.formBuilder.nonNullable.control<number[]>(
      [],
      Validators.required,
    ),
  });

  readonly sugestaoAplicada = signal(false);
  readonly sugestoes = computed(
    () => this.contexto()?.applicability_suggestion?.matches ?? [],
  );

  readonly iniciado = computed(
    () => this.contexto()?.process.status === 'INICIADO',
  );
  readonly podeIniciar = computed(() => {
    const contexto = this.contexto();
    return (
      contexto?.process.status === 'RASCUNHO' &&
      contexto.selection.blockers.length === 0 &&
      !this.selecaoAlterada() &&
      !this.salvando() &&
      !this.iniciando()
    );
  });

  constructor() {
    this.formulario.controls.group_version_ids.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.selecaoAlterada.set(true));
    this.carregar();
  }

  salvarSelecao(): void {
    const contexto = this.contexto();
    if (!contexto || this.formulario.invalid || this.salvando()) {
      this.formulario.markAllAsTouched();
      return;
    }
    this.salvando.set(true);
    this.erro.set('');
    this.aviso.set('');
    this.service
      .salvarSelecao(this.uuid, {
        expected_version: contexto.process.version,
        group_version_ids: this.formulario.controls.group_version_ids.value,
        overrides: contexto.selection.overrides.map(
          ({ sector_code: _sectorCode, ...override }) => override,
        ),
      })
      .pipe(
        finalize(() => this.salvando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (atualizado) => {
          this.aplicar(atualizado);
          this.chaveInicio.set(this.criarChaveIdempotencia());
          this.aviso.set('Seleção do rascunho salva e revalidada.');
        },
        error: (error) =>
          this.erro.set(
            errorMessage(error, 'Não foi possível salvar a seleção do rascunho.'),
          ),
      });
  }

  iniciar(): void {
    const contexto = this.contexto();
    if (!contexto || !this.podeIniciar()) {
      return;
    }
    this.iniciando.set(true);
    this.erro.set('');
    this.aviso.set('');
    this.service
      .iniciar(
        this.uuid,
        contexto.process.version,
        this.chaveInicio(),
      )
      .pipe(
        finalize(() => this.iniciando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (atualizado) => {
          this.aplicar(atualizado);
          this.aviso.set(
            atualizado.idempotency_replayed
              ? 'A confirmação anterior foi recuperada sem duplicar tarefas.'
              : 'Processo iniciado e tarefas geradas.',
          );
        },
        error: (error) =>
          this.erro.set(
            errorMessage(error, 'Não foi possível iniciar o processo.'),
          ),
      });
  }

  protected pedirExclusao(): void {
    this.erro.set('');
    this.aviso.set('');
    this.confirmandoExclusao.set(true);
  }

  protected desistirDaExclusao(): void {
    this.confirmandoExclusao.set(false);
    this.motivoExclusao.set('');
  }

  protected motivo(event: Event): void {
    this.motivoExclusao.set((event.target as HTMLTextAreaElement).value);
  }

  /** Apaga o rascunho de vez; resta a lápide em `SGPD_PROCESS_PURGE`. */
  excluir(): void {
    const contexto = this.contexto();
    if (!contexto || this.excluindo() || !this.motivoExclusao().trim()) {
      return;
    }
    this.excluindo.set(true);
    this.erro.set('');
    this.aviso.set('');
    this.service
      .excluir(
        this.uuid,
        contexto.process.version,
        this.motivoExclusao(),
        this.criarChaveIdempotencia(),
      )
      .pipe(
        finalize(() => this.excluindo.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        // Não há rascunho para recarregar: esta rota deixou de existir.
        next: () => void this.router.navigate(['/fe/processos']),
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível excluir o rascunho.')),
      });
  }

  private carregar(): void {
    this.carregando.set(true);
    this.erro.set('');
    this.service
      .obter(this.uuid)
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (contexto) => this.aplicar(contexto),
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível carregar o rascunho.')),
      });
  }

  private aplicar(contexto: ContextoRascunho): void {
    this.contexto.set(contexto);
    const persistidos = contexto.selection.group_version_ids;
    const sugeridos = contexto.applicability_suggestion?.group_version_ids ?? [];
    // A sugestão só pré-marca um rascunho ainda sem seleção; nada é persistido
    // até o DP salvar, e ele pode desmarcar qualquer grupo antes disso.
    const aplicarSugestao =
      contexto.process.status === 'RASCUNHO' &&
      persistidos.length === 0 &&
      sugeridos.length > 0;
    this.formulario.controls.group_version_ids.setValue(
      aplicarSugestao ? sugeridos : persistidos,
      { emitEvent: false },
    );
    this.sugestaoAplicada.set(aplicarSugestao);
    this.selecaoAlterada.set(aplicarSugestao);
  }

  private criarChaveIdempotencia(): string {
    if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
      return crypto.randomUUID();
    }
    return `start-${this.uuid}-${Date.now()}`;
  }
}
