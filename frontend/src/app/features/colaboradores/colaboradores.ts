import { DatePipe } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { SelectModule } from 'primeng/select';
import { TextareaModule } from 'primeng/textarea';
import type { SelectFilterOptions } from 'primeng/types/select';
import {
  EMPTY,
  Subject,
  Subscription,
  catchError,
  finalize,
  map,
  of,
  switchMap,
  tap,
  timer,
} from 'rxjs';

import {
  FieldErrors,
  errorMessage,
  fieldErrors,
} from '../../core/api/api-error';
import { ColaboradoresService } from './colaboradores.service';
import {
  ColaboradorSenior,
  EmpresaSenior,
  FilialSenior,
  GestorCandidato,
  NovaAberturaProcesso,
  ProcessoAberto,
  TipoColaboradorSenior,
} from './models/colaboradores.models';

type ComRotulo<T> = T & { label: string };

interface RequisicaoColaborador {
  company: number | null;
  branch: number | null;
  employeeType: number | null;
  query: string;
  immediate: boolean;
}

@Component({
  selector: 'app-colaboradores-page',
  imports: [
    DatePipe,
    ReactiveFormsModule,
    ButtonModule,
    InputTextModule,
    MessageModule,
    SelectModule,
    TextareaModule,
  ],
  templateUrl: './colaboradores.html',
  styleUrl: './colaboradores.scss',
})
export class ColaboradoresPage {
  private readonly service = inject(ColaboradoresService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);
  private readonly requisicoesColaborador = new Subject<RequisicaoColaborador>();
  private requisicaoGestores: Subscription | null = null;

  readonly empresa = this.formBuilder.control<number | null>(null);
  readonly filial = this.formBuilder.control<number | null>(null);
  readonly tipoColaborador = this.formBuilder.control<number | null>(null);
  readonly colaborador = this.formBuilder.control<number | null>(null);
  readonly formularioAbertura = this.formBuilder.group({
    manager_user_id: this.formBuilder.control<number | null>(null, Validators.required),
    planned_termination_date: this.formBuilder.nonNullable.control(
      '',
      Validators.required,
    ),
    due_date: this.formBuilder.nonNullable.control('', Validators.required),
    reason: this.formBuilder.nonNullable.control('', Validators.required),
    priority: this.formBuilder.nonNullable.control('', Validators.required),
    notes: this.formBuilder.nonNullable.control(''),
  });

  readonly empresas = signal<ComRotulo<EmpresaSenior>[]>([]);
  readonly filiais = signal<ComRotulo<FilialSenior>[]>([]);
  readonly tiposColaborador = signal<ComRotulo<TipoColaboradorSenior>[]>([]);
  readonly colaboradores = signal<ComRotulo<ColaboradorSenior>[]>([]);
  readonly gestores = signal<ComRotulo<GestorCandidato>[]>([]);

  readonly carregandoEmpresas = signal(false);
  readonly carregandoFiliais = signal(false);
  readonly carregandoTipos = signal(false);
  readonly carregandoColaboradores = signal(false);
  readonly carregandoGestores = signal(false);

  readonly erroEmpresas = signal('');
  readonly erroFiliais = signal('');
  readonly erroTipos = signal('');
  readonly erroColaboradores = signal('');
  readonly erroGestores = signal('');
  readonly buscaColaborador = signal('');
  readonly salvandoProcesso = signal(false);
  readonly erroAbertura = signal('');
  readonly errosAbertura = signal<FieldErrors>({});
  readonly processoAberto = signal<ProcessoAberto | null>(null);

  readonly consultando = computed(
    () =>
      this.carregandoEmpresas() ||
      this.carregandoFiliais() ||
      this.carregandoTipos() ||
      this.carregandoColaboradores(),
  );

  private readonly colaboradorValue = toSignal(this.colaborador.valueChanges, {
    initialValue: this.colaborador.value,
  });

  readonly colaboradorSelecionado = computed(() => {
    const registration = this.colaboradorValue();
    return this.colaboradores().find((item) => item.registration === registration) ?? null;
  });

  constructor() {
    this.configurarCascata();
    this.configurarAbertura();
    this.carregarEmpresas();
  }

  erros(campo: string): string[] {
    return this.errosAbertura()[campo] ?? [];
  }

  filtrarColaboradores(event: Event, options: SelectFilterOptions): void {
    const input = event.target;
    if (!(input instanceof HTMLInputElement)) {
      return;
    }
    const query = input.value.slice(0, 100);
    if (input.value !== query) {
      input.value = query;
    }
    this.buscaColaborador.set(query);
    options.filter?.(event);
    this.solicitarColaboradores(query, false);
  }

  tentarEmpresas(): void {
    this.carregarEmpresas();
  }

  tentarFiliais(): void {
    this.empresa.setValue(this.empresa.value);
  }

  tentarTipos(): void {
    this.filial.setValue(this.filial.value);
  }

  tentarColaboradores(): void {
    this.solicitarColaboradores(this.buscaColaborador(), true);
  }

  tentarGestores(): void {
    const selecionado = this.colaboradorSelecionado();
    if (selecionado) {
      this.carregarGestores(selecionado.company, selecionado.branch);
    }
  }

  abrirProcesso(): void {
    const selecionado = this.colaboradorSelecionado();
    if (
      !selecionado ||
      this.formularioAbertura.invalid ||
      this.salvandoProcesso() ||
      this.processoAberto()
    ) {
      this.formularioAbertura.markAllAsTouched();
      return;
    }
    const value = this.formularioAbertura.getRawValue();
    this.salvandoProcesso.set(true);
    this.erroAbertura.set('');
    this.errosAbertura.set({});
    this.service
      .abrirProcesso({
        company_code: selecionado.company,
        branch_code: selecionado.branch,
        employee_type_code: selecionado.employee_type,
        employee_registration: selecionado.registration,
        manager_user_id: value.manager_user_id as number,
        planned_termination_date: value.planned_termination_date,
        due_date: value.due_date,
        reason: value.reason,
        priority: value.priority,
        notes: value.notes,
      } satisfies NovaAberturaProcesso)
      .pipe(
        finalize(() => this.salvandoProcesso.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (processo) => this.processoAberto.set(processo),
        error: (error) => {
          this.errosAbertura.set(fieldErrors(error));
          this.erroAbertura.set(
            errorMessage(error, 'Não foi possível abrir o processo demissional.'),
          );
        },
      });
  }

  private configurarCascata(): void {
    this.empresa.valueChanges
      .pipe(
        tap(() => this.limparAposEmpresa()),
        switchMap((company) => {
          if (company === null) {
            return EMPTY;
          }
          this.carregandoFiliais.set(true);
          return this.service.listarFiliais(company).pipe(
            catchError((error) => {
              this.erroFiliais.set(
                errorMessage(error, 'Não foi possível consultar as filiais no Senior HCM.'),
              );
              return of(null);
            }),
            finalize(() => this.carregandoFiliais.set(false)),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((pagina) => {
        if (pagina !== null) {
          this.filiais.set(
            pagina.results.map((item) => ({
              ...item,
              label: `${item.branch} — ${item.legal_name}`,
            })),
          );
        }
      });

    this.filial.valueChanges
      .pipe(
        tap(() => this.limparAposFilial()),
        switchMap((branch) => {
          const company = this.empresa.value;
          if (company === null || branch === null) {
            return EMPTY;
          }
          this.carregandoTipos.set(true);
          return this.service.listarTipos(company, branch).pipe(
            catchError((error) => {
              this.erroTipos.set(
                errorMessage(
                  error,
                  'Não foi possível consultar os tipos de colaborador no Senior HCM.',
                ),
              );
              return of(null);
            }),
            finalize(() => this.carregandoTipos.set(false)),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((pagina) => {
        if (pagina !== null) {
          this.tiposColaborador.set(
            pagina.results.map((item) => ({
              ...item,
              label: `${item.employee_type} — ${item.description}`,
            })),
          );
        }
      });

    this.tipoColaborador.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((employeeType) => {
        this.limparAposTipo();
        this.requisicoesColaborador.next({
          company: this.empresa.value,
          branch: this.filial.value,
          employeeType,
          query: '',
          immediate: true,
        });
      });

    this.requisicoesColaborador
      .pipe(
        switchMap((request) =>
          (request.immediate ? of(request) : timer(400).pipe(map(() => request))).pipe(
            switchMap((current) => {
              if (
                current.company === null ||
                current.branch === null ||
                current.employeeType === null
              ) {
                return EMPTY;
              }
              this.colaboradores.set([]);
              this.carregandoColaboradores.set(true);
              return this.service
                .listarColaboradores(
                  current.company,
                  current.branch,
                  current.employeeType,
                  current.query,
                )
                .pipe(
                  catchError((error) => {
                    this.erroColaboradores.set(
                      errorMessage(
                        error,
                        'Não foi possível consultar os colaboradores no Senior HCM.',
                      ),
                    );
                    return of(null);
                  }),
                  finalize(() => this.carregandoColaboradores.set(false)),
                );
            }),
          ),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((pagina) => {
        if (pagina !== null) {
          this.colaboradores.set(
            pagina.results.map((item) => ({
              ...item,
              label: `${item.registration} — ${item.name} — ${item.job_description}`,
            })),
          );
        }
      });
  }

  private configurarAbertura(): void {
    this.colaborador.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((registration) => {
        this.requisicaoGestores?.unsubscribe();
        this.requisicaoGestores = null;
        this.gestores.set([]);
        this.erroGestores.set('');
        this.erroAbertura.set('');
        this.errosAbertura.set({});
        this.processoAberto.set(null);
        this.formularioAbertura.reset({
          manager_user_id: null,
          planned_termination_date: '',
          due_date: '',
          reason: '',
          priority: '',
          notes: '',
        });
        if (registration === null) {
          return;
        }
        const selected = this.colaboradores().find(
          (item) => item.registration === registration,
        );
        if (selected) {
          this.carregarGestores(selected.company, selected.branch);
        }
      });
  }

  private carregarGestores(company: number, branch: number): void {
    if (this.carregandoGestores()) {
      return;
    }
    this.carregandoGestores.set(true);
    this.erroGestores.set('');
    this.requisicaoGestores = this.service
      .listarGestores(company, branch)
      .pipe(
        finalize(() => this.carregandoGestores.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (pagina) =>
          this.gestores.set(
            pagina.results.map((item) => ({
              ...item,
              label: `${item.display_name} — ${item.email}`,
            })),
          ),
        error: (error) =>
          this.erroGestores.set(
            errorMessage(error, 'Não foi possível carregar os gestores cadastrados.'),
          ),
      });
  }

  private carregarEmpresas(): void {
    if (this.carregandoEmpresas()) {
      return;
    }
    this.carregandoEmpresas.set(true);
    this.erroEmpresas.set('');
    this.service
      .listarEmpresas()
      .pipe(
        finalize(() => this.carregandoEmpresas.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (pagina) =>
          this.empresas.set(
            pagina.results.map((item) => ({ ...item, label: `Empresa ${item.company}` })),
          ),
        error: (error) =>
          this.erroEmpresas.set(
            errorMessage(error, 'Não foi possível consultar as empresas no Senior HCM.'),
          ),
      });
  }

  private limparAposEmpresa(): void {
    this.erroFiliais.set('');
    this.filiais.set([]);
    this.filial.setValue(null);
  }

  private limparAposFilial(): void {
    this.erroTipos.set('');
    this.tiposColaborador.set([]);
    this.tipoColaborador.setValue(null);
  }

  private limparAposTipo(): void {
    this.erroColaboradores.set('');
    this.buscaColaborador.set('');
    this.colaboradores.set([]);
    this.colaborador.setValue(null);
  }

  private solicitarColaboradores(query: string, immediate: boolean): void {
    this.erroColaboradores.set('');
    this.colaborador.setValue(null);
    this.requisicoesColaborador.next({
      company: this.empresa.value,
      branch: this.filial.value,
      employeeType: this.tipoColaborador.value,
      query: query.trim().slice(0, 100),
      immediate,
    });
  }
}
