import { DatePipe } from '@angular/common';
import { Component, DestroyRef, computed, inject, input, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { PasswordModule } from 'primeng/password';
import { SelectModule } from 'primeng/select';
import { Observable, finalize } from 'rxjs';

import { FieldErrors, errorMessage, fieldErrors } from '../../core/api/api-error';
import { AuthService } from '../../core/auth/auth.service';
import { Papel } from '../papeis/models/papeis.models';
import { PapeisService } from '../papeis/papeis.service';
import { Atribuicao, UsuarioDetalhe, UsuarioDiretorio } from './models/usuarios.models';
import { UsuariosService } from './usuarios.service';

/** Qual formulário o diálogo está exibindo. */
type Acao = 'editar' | 'senha' | 'papel' | 'revogar' | 'vincular' | 'desvincular' | null;

const TITULOS: Record<Exclude<Acao, null>, string> = {
  editar: 'Editar usuário',
  senha: 'Redefinir senha',
  papel: 'Atribuir papel',
  revogar: 'Revogar atribuição',
  vincular: 'Vincular identidade AD',
  desvincular: 'Desvincular identidade AD',
};

@Component({
  selector: 'app-usuario-detalhe-page',
  imports: [
    ReactiveFormsModule,
    DatePipe,
    ButtonModule,
    CheckboxModule,
    DialogModule,
    InputTextModule,
    MessageModule,
    PasswordModule,
    SelectModule,
  ],
  templateUrl: './usuario-detalhe.html',
  styleUrl: './usuario-detalhe.scss',
})
export class UsuarioDetalhePage {
  private readonly service = inject(UsuariosService);
  private readonly papeisService = inject(PapeisService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);

  /** Vem do parâmetro de rota via `withComponentInputBinding`. */
  readonly id = input.required<string>();

  readonly usuario = signal<UsuarioDetalhe | null>(null);
  readonly carregando = signal(false);
  readonly erroPagina = signal('');

  readonly papeis = signal<Papel[]>([]);
  readonly carregandoPapeis = signal(false);
  readonly podeGerenciarPapeis = computed(() => this.authService.canView('manage_roles'));
  readonly podeVincularAd = computed(() => this.authService.canView('link_ad_identity'));

  readonly acao = signal<Acao>(null);
  readonly salvando = signal(false);
  readonly erroFormulario = signal('');
  readonly errosCampo = signal<FieldErrors>({});
  readonly atribuicaoAlvo = signal<Atribuicao | null>(null);
  readonly buscandoVinculoAd = signal(false);
  readonly resultadosVinculoAd = signal<UsuarioDiretorio[]>([]);
  readonly buscaVinculoAd = this.formBuilder.nonNullable.control('');

  readonly tituloDialogo = computed(() => {
    const acao = this.acao();
    return acao ? TITULOS[acao] : '';
  });

  readonly ativas = computed(() => this.usuario()?.role_assignments.filter((a) => a.is_active) ?? []);
  readonly revogadas = computed(
    () => this.usuario()?.role_assignments.filter((a) => !a.is_active) ?? [],
  );
  readonly avisoSenhaLocal = computed(() => {
    const usuario = this.usuario();
    if (!usuario?.ad_identifier) {
      return '';
    }
    if (!usuario.local_password_allowed) {
      return 'Autenticação AD ativa: a senha local está bloqueada para esta conta.';
    }
    if (usuario.ad_authentication_enabled) {
      return 'Senha local disponível somente pela contingência configurada para superusuário.';
    }
    return 'Autenticação AD desativada: a senha local permanece disponível para testes.';
  });

  readonly escopos = [
    { label: 'Global', value: 'GLOBAL' },
    { label: 'Empresa', value: 'COMPANY' },
    { label: 'Filial', value: 'BRANCH' },
  ];

  readonly formEditar = this.formBuilder.nonNullable.group({
    first_name: ['', [Validators.required]],
    last_name: ['', [Validators.required]],
    email: ['', [Validators.required, Validators.email]],
    is_active: [true],
  });

  readonly formSenha = this.formBuilder.nonNullable.group({
    password: ['', [Validators.required]],
    password_confirm: ['', [Validators.required]],
    must_change_password: [true],
  });

  readonly formPapel = this.formBuilder.nonNullable.group({
    role_id: [null as number | null, [Validators.required]],
    scope_type: ['GLOBAL' as 'GLOBAL' | 'COMPANY' | 'BRANCH', [Validators.required]],
    company_code: [null as number | null],
    branch_code: [null as number | null],
  });

  readonly formVincular = this.formBuilder.nonNullable.group({
    identifier: ['', [Validators.required]],
    username: ['', [Validators.required]],
  });

  constructor() {
    // `id` é signal de entrada: recarrega quando a rota muda.
    queueMicrotask(() => this.carregar());
  }

  erros(campo: string): string[] {
    return this.errosCampo()[campo] ?? [];
  }

  abrir(acao: Exclude<Acao, null>, atribuicao?: Atribuicao): void {
    const usuario = this.usuario();
    if (!usuario) {
      return;
    }
    if (acao === 'senha' && !usuario.local_password_allowed) {
      this.erroPagina.set(
        'A senha local desta conta não pode ser redefinida enquanto a autenticação AD estiver ativa.',
      );
      return;
    }
    this.errosCampo.set({});
    this.erroFormulario.set('');
    this.atribuicaoAlvo.set(atribuicao ?? null);

    if (acao === 'editar') {
      this.formEditar.reset({
        first_name: usuario.first_name,
        last_name: usuario.last_name,
        email: usuario.email,
        is_active: usuario.is_active,
      });
    }
    if (acao === 'senha') {
      this.formSenha.reset({ must_change_password: true });
    }
    if (acao === 'papel') {
      this.formPapel.reset({ scope_type: 'GLOBAL' });
      if (this.papeis().length === 0) {
        this.carregarPapeis();
      }
    }
    if (acao === 'vincular') {
      this.formVincular.reset({ username: usuario.username, identifier: '' });
      this.buscaVinculoAd.reset(usuario.username);
      this.resultadosVinculoAd.set([]);
    }
    this.acao.set(acao);
  }

  fechar(): void {
    this.acao.set(null);
  }

  buscarVinculoAd(): void {
    const busca = this.buscaVinculoAd.value.trim();
    if (busca.length < 2 || this.buscandoVinculoAd()) {
      return;
    }
    this.buscandoVinculoAd.set(true);
    this.erroFormulario.set('');
    this.service
      .buscarUsuariosAd(busca)
      .pipe(
        finalize(() => this.buscandoVinculoAd.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (pagina) => this.resultadosVinculoAd.set(pagina.results),
        error: (error) => this.erroFormulario.set(errorMessage(error)),
      });
  }

  selecionarVinculoAd(identity: UsuarioDiretorio): void {
    this.formVincular.patchValue({
      identifier: identity.identifier,
      username: identity.username,
    });
    this.resultadosVinculoAd.set([identity]);
  }

  confirmar(): void {
    const usuario = this.usuario();
    const acao = this.acao();
    if (!usuario || !acao || this.salvando()) {
      return;
    }

    const execucao = this.montarExecucao(usuario, acao);
    if (!execucao) {
      return;
    }

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
          this.acao.set(null);
          this.carregar();
        },
        error: (error) => {
          this.errosCampo.set(fieldErrors(error));
          this.erroFormulario.set(errorMessage(error));
        },
      });
  }

  private montarExecucao(usuario: UsuarioDetalhe, acao: Exclude<Acao, null>): Observable<unknown> | null {
    switch (acao) {
      case 'editar': {
        if (this.formEditar.invalid) {
          this.formEditar.markAllAsTouched();
          return null;
        }
        return this.service.atualizar(usuario.id, {
          version: usuario.version,
          ...this.formEditar.getRawValue(),
        });
      }
      case 'senha': {
        if (!usuario.local_password_allowed) {
          this.erroFormulario.set(
            'A senha local desta conta é gerenciada pelo Active Directory.',
          );
          return null;
        }
        if (this.formSenha.invalid) {
          this.formSenha.markAllAsTouched();
          return null;
        }
        return this.service.redefinirSenha(usuario.id, this.formSenha.getRawValue());
      }
      case 'papel': {
        if (!this.validarAtribuicaoPapel()) {
          return null;
        }
        const valor = this.formPapel.getRawValue();
        return this.service.atribuirPapel(usuario.id, {
          role_id: valor.role_id as number,
          scope_type: valor.scope_type,
          company_code: valor.scope_type === 'GLOBAL' ? null : valor.company_code,
          branch_code: valor.scope_type === 'BRANCH' ? valor.branch_code : null,
          valid_until: null,
        });
      }
      case 'revogar': {
        const alvo = this.atribuicaoAlvo();
        if (!alvo) {
          return null;
        }
        return this.service.revogarAtribuicao(alvo.id);
      }
      case 'vincular': {
        if (this.formVincular.invalid) {
          this.formVincular.markAllAsTouched();
          return null;
        }
        return this.service.vincularAd(usuario.id, {
          version: usuario.version,
          ...this.formVincular.getRawValue(),
        });
      }
      case 'desvincular': {
        return this.service.desvincularAd(usuario.id, usuario.version);
      }
    }
  }

  private validarAtribuicaoPapel(): boolean {
    const valor = this.formPapel.getRawValue();
    if (this.formPapel.invalid || valor.role_id === null) {
      this.formPapel.markAllAsTouched();
      this.erroFormulario.set('Selecione o papel que será atribuído.');
      return false;
    }
    if (valor.scope_type !== 'GLOBAL' && valor.company_code === null) {
      this.erroFormulario.set('Informe a empresa do escopo do papel.');
      return false;
    }
    if (valor.scope_type === 'BRANCH' && valor.branch_code === null) {
      this.erroFormulario.set('Informe a filial do escopo do papel.');
      return false;
    }
    return true;
  }

  private carregar(): void {
    this.carregando.set(true);
    this.erroPagina.set('');
    this.service
      .detalhe(Number(this.id()))
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (usuario) => this.usuario.set(usuario),
        error: (error) => this.erroPagina.set(errorMessage(error, 'Usuário não encontrado.')),
      });
  }

  private carregarPapeis(): void {
    this.carregandoPapeis.set(true);
    this.papeisService
      .listar()
      .pipe(
        finalize(() => this.carregandoPapeis.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (pagina) => this.papeis.set(pagina.results.filter((papel) => papel.is_active)),
        error: (error) =>
          this.erroFormulario.set(
            errorMessage(error, 'Não foi possível carregar os papéis disponíveis.'),
          ),
      });
  }
}
