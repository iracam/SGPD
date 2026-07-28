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
import { TextareaModule } from 'primeng/textarea';
import { Observable, finalize } from 'rxjs';

import { FieldErrors, errorMessage, fieldErrors } from '../../core/api/api-error';
import { AuthService } from '../../core/auth/auth.service';
import { Papel } from '../papeis/models/papeis.models';
import { PapeisService } from '../papeis/papeis.service';
import { Atribuicao, UsuarioDetalhe } from './models/usuarios.models';
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
    ButtonModule,
    CheckboxModule,
    DialogModule,
    InputTextModule,
    MessageModule,
    PasswordModule,
    SelectModule,
    TextareaModule,
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
  readonly podeGerenciarPapeis = computed(() => this.authService.canView('manage_roles'));
  readonly podeVincularAd = computed(() => this.authService.canView('link_ad_identity'));

  readonly acao = signal<Acao>(null);
  readonly salvando = signal(false);
  readonly erroFormulario = signal('');
  readonly errosCampo = signal<FieldErrors>({});
  readonly atribuicaoAlvo = signal<Atribuicao | null>(null);

  readonly tituloDialogo = computed(() => {
    const acao = this.acao();
    return acao ? TITULOS[acao] : '';
  });

  readonly ativas = computed(() => this.usuario()?.role_assignments.filter((a) => a.is_active) ?? []);
  readonly revogadas = computed(
    () => this.usuario()?.role_assignments.filter((a) => !a.is_active) ?? [],
  );

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
    reason: ['', [Validators.required]],
  });

  readonly formSenha = this.formBuilder.nonNullable.group({
    password: ['', [Validators.required]],
    password_confirm: ['', [Validators.required]],
    must_change_password: [true],
    reason: ['', [Validators.required]],
  });

  readonly formPapel = this.formBuilder.nonNullable.group({
    role_id: [null as number | null, [Validators.required]],
    scope_type: ['GLOBAL' as 'GLOBAL' | 'COMPANY' | 'BRANCH', [Validators.required]],
    company_code: [null as number | null],
    branch_code: [null as number | null],
    reason: ['', [Validators.required]],
  });

  readonly formMotivo = this.formBuilder.nonNullable.group({
    reason: ['', [Validators.required]],
  });

  readonly formVincular = this.formBuilder.nonNullable.group({
    identifier: ['', [Validators.required]],
    username: ['', [Validators.required]],
    reason: ['', [Validators.required]],
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
    this.errosCampo.set({});
    this.erroFormulario.set('');
    this.atribuicaoAlvo.set(atribuicao ?? null);

    if (acao === 'editar') {
      this.formEditar.reset({
        first_name: usuario.first_name,
        last_name: usuario.last_name,
        email: usuario.email,
        is_active: usuario.is_active,
        reason: '',
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
    if (acao === 'revogar' || acao === 'desvincular') {
      this.formMotivo.reset();
    }
    if (acao === 'vincular') {
      this.formVincular.reset({ username: usuario.username, identifier: '', reason: '' });
    }
    this.acao.set(acao);
  }

  fechar(): void {
    this.acao.set(null);
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
        if (this.formSenha.invalid) {
          this.formSenha.markAllAsTouched();
          return null;
        }
        return this.service.redefinirSenha(usuario.id, this.formSenha.getRawValue());
      }
      case 'papel': {
        if (this.formPapel.invalid) {
          this.formPapel.markAllAsTouched();
          return null;
        }
        const valor = this.formPapel.getRawValue();
        return this.service.atribuirPapel(usuario.id, {
          role_id: valor.role_id as number,
          scope_type: valor.scope_type,
          company_code: valor.scope_type === 'GLOBAL' ? null : valor.company_code,
          branch_code: valor.scope_type === 'BRANCH' ? valor.branch_code : null,
          valid_until: null,
          reason: valor.reason,
        });
      }
      case 'revogar': {
        const alvo = this.atribuicaoAlvo();
        if (this.formMotivo.invalid || !alvo) {
          this.formMotivo.markAllAsTouched();
          return null;
        }
        return this.service.revogarAtribuicao(alvo.id, this.formMotivo.getRawValue().reason);
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
        if (this.formMotivo.invalid) {
          this.formMotivo.markAllAsTouched();
          return null;
        }
        return this.service.desvincularAd(
          usuario.id,
          usuario.version,
          this.formMotivo.getRawValue().reason,
        );
      }
    }
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
    this.papeisService
      .listar()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (pagina) => this.papeis.set(pagina.results.filter((papel) => papel.is_active)),
        error: () => undefined,
      });
  }
}
