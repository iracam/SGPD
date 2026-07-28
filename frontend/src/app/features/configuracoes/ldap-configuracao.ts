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
  LdapConfiguration,
  LdapConfigurationPayload,
  LdapDirectoryGroup,
  LdapValidationResult,
} from './models/configuracoes.models';

@Component({
  selector: 'app-ldap-configuracao-page',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    ButtonModule,
    CheckboxModule,
    InputTextModule,
    MessageModule,
    PasswordModule,
  ],
  templateUrl: './ldap-configuracao.html',
  styleUrl: './ldap-configuracao.scss',
})
export class LdapConfiguracaoPage {
  private readonly service = inject(ConfiguracoesService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  readonly configuracao = signal<LdapConfiguration | null>(null);
  readonly carregando = signal(true);
  readonly salvando = signal(false);
  readonly validando = signal(false);
  readonly testando = signal(false);
  readonly enviandoCertificado = signal(false);
  readonly validandoCertificado = signal(false);
  readonly buscandoGrupos = signal(false);
  readonly erroPagina = signal('');
  readonly erroFormulario = signal('');
  readonly sucesso = signal('');
  readonly erroCertificado = signal('');
  readonly sucessoCertificado = signal('');
  readonly errosCampo = signal<FieldErrors>({});
  readonly resultadoValidacao = signal<LdapValidationResult | null>(null);
  readonly certificadoSelecionado = signal<File | null>(null);
  readonly gruposEncontrados = signal<LdapDirectoryGroup[]>([]);
  readonly buscaGrupo = this.formBuilder.nonNullable.control('');

  readonly senhaConfigurada = computed(
    () => this.configuracao()?.bind_password_configured ?? false,
  );

  readonly formulario = this.formBuilder.nonNullable.group({
    enabled: [false],
    authentication_enabled: [false],
    server_address: ['', [Validators.maxLength(512)]],
    use_tls: [true],
    bind_dn: ['', [Validators.maxLength(512)]],
    bind_password: ['', [Validators.maxLength(1024)]],
    user_search_base: ['', [Validators.maxLength(2000)]],
    group_search_base: ['', [Validators.maxLength(2000)]],
    required_group_dn: ['', [Validators.maxLength(2000)]],
    connect_timeout_seconds: [5, [Validators.required, Validators.min(1), Validators.max(300)]],
    receive_timeout_seconds: [10, [Validators.required, Validators.min(1), Validators.max(300)]],
    page_size: [100, [Validators.required, Validators.min(1), Validators.max(1000)]],
    result_limit: [50, [Validators.required, Validators.min(1), Validators.max(200)]],
    nested_group_search: [true],
    local_superuser_fallback: [true],
    user_extra_filter: ['', [Validators.maxLength(2000)]],
  });

  constructor() {
    this.carregar();
  }

  erros(campo: string): string[] {
    return this.errosCampo()[campo] ?? [];
  }

  tlsAtivo(): boolean {
    return this.formulario.controls.use_tls.value;
  }

  salvar(): void {
    if (this.formulario.invalid || this.salvando()) {
      this.formulario.markAllAsTouched();
      return;
    }
    this.salvando.set(true);
    this.limparMensagens();
    this.service
      .salvarLdap(this.payload())
      .pipe(
        finalize(() => this.salvando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (configuracao) => {
          this.aplicar(configuracao);
          this.sucesso.set('Configuração LDAP salva e auditada.');
        },
        error: (error) => {
          this.errosCampo.set(fieldErrors(error));
          this.erroFormulario.set(
            errorMessage(error, 'Não foi possível salvar a configuração LDAP.'),
          );
        },
      });
  }

  validarInformacoes(): void {
    if (this.validando()) {
      return;
    }
    this.validando.set(true);
    this.limparMensagens();
    this.service
      .validarLdap(this.payload())
      .pipe(
        finalize(() => this.validando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (resultado) => {
          this.resultadoValidacao.set(resultado);
          if (resultado.valid) {
            this.sucesso.set('Estrutura e política da configuração são válidas.');
          }
        },
        error: (error) => {
          this.errosCampo.set(fieldErrors(error));
          this.erroFormulario.set(errorMessage(error));
        },
      });
  }

  selecionarCertificado(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.certificadoSelecionado.set(input.files?.[0] ?? null);
    this.erroCertificado.set('');
    this.sucessoCertificado.set('');
  }

  enviarCertificado(): void {
    const arquivo = this.certificadoSelecionado();
    const configuracao = this.configuracao();
    if (!arquivo || !configuracao || this.enviandoCertificado()) {
      if (!arquivo) {
        this.erroCertificado.set('Selecione um certificado PEM, CRT ou CER.');
      }
      return;
    }
    this.enviandoCertificado.set(true);
    this.limparMensagens();
    this.service
      .enviarCertificado(configuracao.version, arquivo)
      .pipe(
        finalize(() => this.enviandoCertificado.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (atualizada) => {
          this.aplicar(atualizada);
          this.certificadoSelecionado.set(null);
          this.sucessoCertificado.set(
            'Certificado validado, armazenado em área privada e auditado.',
          );
        },
        error: (error) => {
          this.errosCampo.set(fieldErrors(error));
          this.erroCertificado.set(
            errorMessage(error, 'Não foi possível validar e enviar o certificado.'),
          );
        },
      });
  }

  validarCertificado(): void {
    if (this.validandoCertificado()) {
      return;
    }
    this.validandoCertificado.set(true);
    this.limparMensagens();
    this.service
      .validarCertificado()
      .pipe(
        finalize(() => this.validandoCertificado.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () =>
          this.sucessoCertificado.set('Certificado e hash revalidados com sucesso.'),
        error: (error) => this.erroCertificado.set(errorMessage(error)),
      });
  }

  buscarGrupos(): void {
    const busca = this.buscaGrupo.value.trim();
    if (busca.length < 2 || this.buscandoGrupos()) {
      return;
    }
    this.buscandoGrupos.set(true);
    this.erroFormulario.set('');
    this.service
      .buscarGruposLdap(busca)
      .pipe(
        finalize(() => this.buscandoGrupos.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (pagina) => this.gruposEncontrados.set(pagina.results),
        error: (error) => this.erroFormulario.set(errorMessage(error)),
      });
  }

  selecionarGrupo(grupo: LdapDirectoryGroup): void {
    this.formulario.controls.required_group_dn.setValue(grupo.distinguished_name);
    this.formulario.controls.required_group_dn.markAsDirty();
    this.gruposEncontrados.set([]);
  }

  testarConexao(): void {
    if (this.testando()) {
      return;
    }
    this.testando.set(true);
    this.limparMensagens();
    this.service
      .testarConexao()
      .pipe(
        finalize(() => this.testando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (resultado) => {
          const atual = this.configuracao();
          if (atual) {
            this.configuracao.set({
              ...atual,
              connection_test: {
                tested_at: resultado.tested_at,
                success: true,
                duration_ms: resultado.duration_ms,
                tested_by: null,
              },
            });
          }
          this.sucesso.set(
            `Bind e RootDSE validados em ${resultado.duration_ms} ms, sem listar usuários.`,
          );
        },
        error: (error) => this.erroFormulario.set(errorMessage(error)),
      });
  }

  formatarData(value: string | null): string {
    if (!value) {
      return '—';
    }
    return new Intl.DateTimeFormat('pt-BR', {
      dateStyle: 'short',
      timeStyle: 'short',
    }).format(new Date(value));
  }

  private carregar(): void {
    this.carregando.set(true);
    this.erroPagina.set('');
    this.service
      .carregarLdap()
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (configuracao) => this.aplicar(configuracao),
        error: (error) => this.erroPagina.set(errorMessage(error)),
      });
  }

  private aplicar(configuracao: LdapConfiguration): void {
    this.configuracao.set(configuracao);
    this.formulario.patchValue({
      enabled: configuracao.enabled,
      authentication_enabled: configuracao.authentication_enabled,
      server_address: configuracao.server_address,
      use_tls: configuracao.use_tls,
      bind_dn: configuracao.bind_dn,
      bind_password: '',
      user_search_base: configuracao.user_search_base,
      group_search_base: configuracao.group_search_base,
      required_group_dn: configuracao.required_group_dn,
      connect_timeout_seconds: configuracao.connect_timeout_seconds,
      receive_timeout_seconds: configuracao.receive_timeout_seconds,
      page_size: configuracao.page_size,
      result_limit: configuracao.result_limit,
      nested_group_search: configuracao.nested_group_search,
      local_superuser_fallback: configuracao.local_superuser_fallback,
      user_extra_filter: configuracao.user_extra_filter,
    });
    this.formulario.markAsPristine();
    this.buscaGrupo.reset();
    this.gruposEncontrados.set([]);
    this.resultadoValidacao.set(null);
  }

  private payload(): LdapConfigurationPayload {
    const raw = this.formulario.getRawValue();
    return {
      version: this.configuracao()?.version ?? 0,
      ...raw,
    };
  }

  private limparMensagens(): void {
    this.erroFormulario.set('');
    this.erroCertificado.set('');
    this.errosCampo.set({});
    this.sucesso.set('');
    this.sucessoCertificado.set('');
    this.resultadoValidacao.set(null);
  }
}
