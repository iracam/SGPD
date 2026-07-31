import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { PasswordModule } from 'primeng/password';
import { finalize } from 'rxjs';

import { FieldErrors, errorMessage, fieldErrors } from '../../core/api/api-error';
import { ConfiguracoesService } from './configuracoes.service';
import {
  EmailConfiguration,
  EmailConfigurationPayload,
  EmailValidationResult,
} from './models/configuracoes.models';

/**
 * Central de e-mail e notificações (ADR-050).
 *
 * O `.env` continua sendo apenas o baseline do primeiro boot: o que vale em
 * runtime é o que está gravado aqui. A senha nunca volta do servidor — campo em
 * branco preserva a vigente.
 */
@Component({
  selector: 'app-email-configuracao-page',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    ButtonModule,
    CheckboxModule,
    InputTextModule,
    MessageModule,
    PasswordModule,
  ],
  templateUrl: './email-configuracao.html',
  styleUrl: './email-configuracao.scss',
})
export class EmailConfiguracaoPage {
  private readonly service = inject(ConfiguracoesService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  readonly configuracao = signal<EmailConfiguration | null>(null);
  readonly carregando = signal(true);
  readonly salvando = signal(false);
  readonly validando = signal(false);
  readonly testando = signal(false);
  readonly erroPagina = signal('');
  readonly erroFormulario = signal('');
  readonly sucesso = signal('');
  readonly errosCampo = signal<FieldErrors>({});
  readonly resultadoValidacao = signal<EmailValidationResult | null>(null);

  readonly senhaConfigurada = computed(() => this.configuracao()?.password_configured ?? false);
  readonly origemBanco = computed(() => this.configuracao()?.source === 'database');

  readonly formulario = this.formBuilder.nonNullable.group({
    enabled: [false],
    host: ['', [Validators.maxLength(255)]],
    port: [587, [Validators.required, Validators.min(1), Validators.max(65535)]],
    use_tls: [true],
    username: ['', [Validators.maxLength(255)]],
    password: ['', [Validators.maxLength(1024)]],
    timeout_seconds: [10, [Validators.required, Validators.min(1), Validators.max(300)]],
    default_from_email: ['', [Validators.maxLength(254)]],
    base_url: ['', [Validators.maxLength(255)]],
    max_attempts: [5, [Validators.required, Validators.min(1), Validators.max(20)]],
    batch_size: [50, [Validators.required, Validators.min(1), Validators.max(500)]],
    stale_minutes: [15, [Validators.required, Validators.min(1), Validators.max(1440)]],
    task_due_soon_hours: [48, [Validators.required, Validators.min(1), Validators.max(720)]],
    task_due_imminent_hours: [24, [Validators.required, Validators.min(1), Validators.max(720)]],
    task_critical_hours: [48, [Validators.required, Validators.min(1), Validators.max(720)]],
    process_due_soon_hours: [72, [Validators.required, Validators.min(1), Validators.max(720)]],
  });

  constructor() {
    this.carregar();
  }

  protected formatarData(value: string | null): string {
    if (!value) {
      return '—';
    }
    return new Intl.DateTimeFormat('pt-BR', {
      dateStyle: 'short',
      timeStyle: 'short',
    }).format(new Date(value));
  }

  protected erros(campo: string): string[] {
    return this.errosCampo()[campo] ?? [];
  }

  protected salvar(): void {
    if (this.formulario.invalid || this.salvando()) {
      this.formulario.markAllAsTouched();
      return;
    }
    this.salvando.set(true);
    this.limparMensagens();
    this.service
      .salvarEmail(this.payload())
      .pipe(
        finalize(() => this.salvando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (configuracao) => {
          this.aplicar(configuracao);
          this.sucesso.set('Configuração de e-mail salva e auditada.');
        },
        error: (error) => {
          this.errosCampo.set(fieldErrors(error));
          this.erroFormulario.set(
            errorMessage(error, 'Não foi possível salvar a configuração de e-mail.'),
          );
        },
      });
  }

  protected validarInformacoes(): void {
    if (this.validando()) {
      return;
    }
    this.validando.set(true);
    this.limparMensagens();
    this.service
      .validarEmail(this.payload())
      .pipe(
        finalize(() => this.validando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (resultado) => {
          this.resultadoValidacao.set(resultado);
          if (resultado.valid) {
            this.sucesso.set('A configuração informada é válida.');
          }
        },
        error: (error) => {
          this.errosCampo.set(fieldErrors(error));
          this.erroFormulario.set(errorMessage(error));
        },
      });
  }

  protected testarEnvio(): void {
    if (this.testando()) {
      return;
    }
    this.testando.set(true);
    this.limparMensagens();
    this.service
      .testarEnvioEmail()
      .pipe(
        finalize(() => this.testando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (resultado) => {
          this.sucesso.set(`Mensagem de prova enviada para ${resultado.recipient}.`);
          this.carregar();
        },
        error: (error) => {
          this.errosCampo.set(fieldErrors(error));
          this.erroFormulario.set(
            errorMessage(error, 'Não foi possível enviar a mensagem de prova.'),
          );
        },
      });
  }

  private carregar(): void {
    this.carregando.set(true);
    this.service
      .carregarEmail()
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (configuracao) => this.aplicar(configuracao),
        error: (error) =>
          this.erroPagina.set(
            errorMessage(error, 'Não foi possível carregar a configuração de e-mail.'),
          ),
      });
  }

  private aplicar(configuracao: EmailConfiguration): void {
    this.configuracao.set(configuracao);
    this.resultadoValidacao.set(null);
    this.formulario.patchValue({
      enabled: configuracao.enabled,
      host: configuracao.host,
      port: configuracao.port,
      use_tls: configuracao.use_tls,
      username: configuracao.username,
      // A senha nunca volta do servidor: o campo recomeça vazio e só substitui
      // o segredo quando o administrador digita um novo.
      password: '',
      timeout_seconds: configuracao.timeout_seconds,
      default_from_email: configuracao.default_from_email,
      base_url: configuracao.base_url,
      max_attempts: configuracao.max_attempts,
      batch_size: configuracao.batch_size,
      stale_minutes: configuracao.stale_minutes,
      task_due_soon_hours: configuracao.task_due_soon_hours,
      task_due_imminent_hours: configuracao.task_due_imminent_hours,
      task_critical_hours: configuracao.task_critical_hours,
      process_due_soon_hours: configuracao.process_due_soon_hours,
    });
  }

  private payload(): EmailConfigurationPayload {
    const valores = this.formulario.getRawValue();
    return {
      ...valores,
      version: this.configuracao()?.version ?? 0,
    };
  }

  private limparMensagens(): void {
    this.erroFormulario.set('');
    this.sucesso.set('');
    this.errosCampo.set({});
  }
}
