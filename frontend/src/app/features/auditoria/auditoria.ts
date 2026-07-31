import { DatePipe } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { SelectModule } from 'primeng/select';
import { finalize } from 'rxjs';

import { errorMessage } from '../../core/api/api-error';
import { AuditoriaService } from './auditoria.service';
import { EventoAuditoria } from './models/auditoria.models';

const PAGINA = 50;

@Component({
  selector: 'app-auditoria-page',
  imports: [DatePipe, ReactiveFormsModule, ButtonModule, MessageModule, SelectModule],
  templateUrl: './auditoria.html',
  styleUrl: './auditoria.scss',
})
export class AuditoriaPage {
  private readonly service = inject(AuditoriaService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  readonly eventos = signal<EventoAuditoria[]>([]);
  readonly carregando = signal(false);
  readonly erroPagina = signal('');
  readonly offset = signal(0);
  readonly vazio = computed(() => !this.carregando() && this.eventos().length === 0);

  /**
   * A API pagina sem `COUNT(*)`, por decisão de desempenho: não há total. A
   * navegação assume que há próxima página quando a atual veio cheia.
   */
  readonly temProxima = computed(() => this.eventos().length === PAGINA);
  readonly temAnterior = computed(() => this.offset() > 0);

  readonly tipos = [
    { label: 'Todos os eventos', value: null },
    { label: 'Login', value: 'LOGIN' },
    { label: 'Falha de autenticação', value: 'LOGIN_FAILED' },
    { label: 'Logout', value: 'LOGOUT' },
    { label: 'Usuário criado', value: 'USER_CREATED' },
    { label: 'Usuário atualizado', value: 'USER_UPDATED' },
    { label: 'Senha alterada', value: 'PASSWORD_CHANGED' },
    { label: 'Senha redefinida', value: 'PASSWORD_RESET' },
    { label: 'Papel criado', value: 'ROLE_CREATED' },
    { label: 'Papel atualizado', value: 'ROLE_UPDATED' },
    { label: 'Papel atribuído', value: 'ROLE_ASSIGNED' },
    { label: 'Papel revogado', value: 'ROLE_REVOKED' },
    { label: 'AD vinculado', value: 'AD_LINKED' },
    { label: 'AD desvinculado', value: 'AD_UNLINKED' },
  ];

  readonly tipo = this.formBuilder.control<string | null>(null);

  // Enum cru nunca chega ao usuário (ADR-047); tipo desconhecido cai no próprio código.
  rotuloEvento(tipo: string): string {
    return this.tipos.find((opcao) => opcao.value === tipo)?.label ?? tipo;
  }

  constructor() {
    this.carregar();
    this.tipo.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.offset.set(0);
      this.carregar();
    });
  }

  proxima(): void {
    this.offset.update((atual) => atual + PAGINA);
    this.carregar();
  }

  anterior(): void {
    this.offset.update((atual) => Math.max(0, atual - PAGINA));
    this.carregar();
  }

  private carregar(): void {
    this.carregando.set(true);
    this.erroPagina.set('');
    this.service
      .listar({ eventType: this.tipo.value }, this.offset(), PAGINA)
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (pagina) => this.eventos.set(pagina.results),
        error: (error) => this.erroPagina.set(errorMessage(error)),
      });
  }
}
