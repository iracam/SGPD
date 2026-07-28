import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { PasswordModule } from 'primeng/password';
import { TextareaModule } from 'primeng/textarea';
import { debounceTime, distinctUntilChanged, finalize, switchMap } from 'rxjs';

import { FieldErrors, errorMessage, fieldErrors } from '../../core/api/api-error';
import { AuthService } from '../../core/auth/auth.service';
import {
  DiretorioStatus,
  Usuario,
  UsuarioDiretorio,
} from './models/usuarios.models';
import { UsuariosService } from './usuarios.service';

@Component({
  selector: 'app-usuarios-page',
  imports: [
    ReactiveFormsModule,
    ButtonModule,
    CheckboxModule,
    DialogModule,
    InputTextModule,
    MessageModule,
    PasswordModule,
    TextareaModule,
  ],
  templateUrl: './usuarios.html',
  styleUrl: './usuarios.scss',
})
export class UsuariosPage {
  private readonly service = inject(UsuariosService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly authService = inject(AuthService);

  readonly usuarios = signal<Usuario[]>([]);
  readonly carregando = signal(false);
  readonly erroLista = signal('');
  readonly vazio = computed(() => !this.carregando() && this.usuarios().length === 0);
  readonly podeImportarAd = computed(
    () =>
      this.authService.canView('link_ad_identity') && this.authService.canView('manage_users'),
  );

  readonly busca = this.formBuilder.nonNullable.control('');

  readonly dialogoAberto = signal(false);
  readonly salvando = signal(false);
  readonly erroFormulario = signal('');
  readonly errosCampo = signal<FieldErrors>({});

  readonly formulario = this.formBuilder.nonNullable.group({
    username: ['', [Validators.required]],
    first_name: ['', [Validators.required]],
    last_name: ['', [Validators.required]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
    password_confirm: ['', [Validators.required]],
    must_change_password: [true],
    reason: ['', [Validators.required]],
  });

  readonly dialogoAdAberto = signal(false);
  readonly statusDiretorio = signal<DiretorioStatus | null>(null);
  readonly carregandoStatusAd = signal(false);
  readonly buscandoUsuariosAd = signal(false);
  readonly criandoDoAd = signal<string | null>(null);
  readonly erroDiretorio = signal('');
  readonly usuariosAd = signal<UsuarioDiretorio[]>([]);
  readonly buscaUsuarioAd = this.formBuilder.nonNullable.control('');

  constructor() {
    this.carregar('');
    this.busca.valueChanges
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((termo) => {
          this.carregando.set(true);
          return this.service.listar(termo).pipe(finalize(() => this.carregando.set(false)));
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (pagina) => this.usuarios.set(pagina.results),
        error: (error) => this.erroLista.set(errorMessage(error)),
      });
  }

  erros(campo: string): string[] {
    return this.errosCampo()[campo] ?? [];
  }

  abrirDialogo(): void {
    this.formulario.reset({ must_change_password: true });
    this.errosCampo.set({});
    this.erroFormulario.set('');
    this.dialogoAberto.set(true);
  }

  abrirDetalhe(usuario: Usuario): void {
    void this.router.navigate(['/fe/usuarios', usuario.id]);
  }

  abrirDialogoAd(): void {
    this.dialogoAdAberto.set(true);
    this.statusDiretorio.set(null);
    this.erroDiretorio.set('');
    this.usuariosAd.set([]);
    this.buscaUsuarioAd.reset();
    this.carregandoStatusAd.set(true);
    this.service
      .statusDiretorio()
      .pipe(
        finalize(() => this.carregandoStatusAd.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (status) => this.statusDiretorio.set(status),
        error: (error) => this.erroDiretorio.set(errorMessage(error)),
      });
  }

  buscarUsuariosAd(): void {
    const busca = this.buscaUsuarioAd.value.trim();
    if (busca.length < 2 || this.buscandoUsuariosAd()) {
      return;
    }
    this.buscandoUsuariosAd.set(true);
    this.erroDiretorio.set('');
    this.service
      .buscarUsuariosAd(busca)
      .pipe(
        finalize(() => this.buscandoUsuariosAd.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (pagina) => this.usuariosAd.set(pagina.results),
        error: (error) => this.erroDiretorio.set(errorMessage(error)),
      });
  }

  criarDoAd(identity: UsuarioDiretorio): void {
    if (!identity.can_import || identity.local_user || this.criandoDoAd()) {
      return;
    }
    this.criandoDoAd.set(identity.identifier);
    this.erroDiretorio.set('');
    this.service
      .criarDoAd(identity.identifier)
      .pipe(
        finalize(() => this.criandoDoAd.set(null)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (usuario) => {
          this.dialogoAdAberto.set(false);
          this.carregar(this.busca.value);
          this.abrirDetalhe(usuario);
        },
        error: (error) => this.erroDiretorio.set(errorMessage(error)),
      });
  }

  requisitosAusentes(identity: UsuarioDiretorio): string {
    const rotulos: Record<string, string> = {
      sAMAccountName: 'login',
      givenName: 'nome',
      sn: 'sobrenome',
      mail: 'e-mail',
    };
    return identity.missing_import_fields
      .map((campo) => rotulos[campo] ?? campo)
      .join(', ');
  }

  abrirUsuarioLocal(id: number): void {
    this.dialogoAdAberto.set(false);
    void this.router.navigate(['/fe/usuarios', id]);
  }

  salvar(): void {
    if (this.formulario.invalid || this.salvando()) {
      this.formulario.markAllAsTouched();
      return;
    }
    this.salvando.set(true);
    this.erroFormulario.set('');
    this.errosCampo.set({});

    this.service
      .criar(this.formulario.getRawValue())
      .pipe(
        finalize(() => this.salvando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () => {
          this.dialogoAberto.set(false);
          this.carregar(this.busca.value);
        },
        error: (error) => {
          this.errosCampo.set(fieldErrors(error));
          this.erroFormulario.set(errorMessage(error, 'Não foi possível criar o usuário.'));
        },
      });
  }

  private carregar(termo: string): void {
    this.carregando.set(true);
    this.erroLista.set('');
    this.service
      .listar(termo)
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (pagina) => this.usuarios.set(pagina.results),
        error: (error) => this.erroLista.set(errorMessage(error)),
      });
  }
}
