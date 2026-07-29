import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  FormBuilder,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { InputNumberModule } from 'primeng/inputnumber';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { SelectModule } from 'primeng/select';
import { TagModule } from 'primeng/tag';
import { TextareaModule } from 'primeng/textarea';
import { finalize, forkJoin } from 'rxjs';

import { errorMessage } from '../../core/api/api-error';
import {
  GrupoValidacao,
  NovoGrupo,
  NovoTemplate,
  SetorWorkflow,
  TemplateChecklist,
  TipoRespostaChecklist,
} from './models/workflow-config.models';
import { WorkflowConfigService } from './workflow-config.service';

type PerguntaForm = FormGroup<{
  code: FormControl<string>;
  question: FormControl<string>;
  response_type: FormControl<TipoRespostaChecklist>;
  is_required: FormControl<boolean>;
  blocks_process: FormControl<boolean>;
  requires_evidence: FormControl<boolean>;
  allows_pending: FormControl<boolean>;
}>;

type RegraForm = FormGroup<{
  sector_id: FormControl<number | null>;
  template_version_id: FormControl<number | null>;
  is_required: FormControl<boolean>;
  blocks_process: FormControl<boolean>;
  due_hours_override: FormControl<number | null>;
}>;

@Component({
  selector: 'app-workflow-config-page',
  imports: [
    ReactiveFormsModule,
    ButtonModule,
    CheckboxModule,
    InputNumberModule,
    InputTextModule,
    MessageModule,
    SelectModule,
    TagModule,
    TextareaModule,
  ],
  templateUrl: './workflow-config.html',
  styleUrl: './workflow-config.scss',
})
export class WorkflowConfigPage {
  private readonly service = inject(WorkflowConfigService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  readonly setores = signal<SetorWorkflow[]>([]);
  readonly templates = signal<TemplateChecklist[]>([]);
  readonly grupos = signal<GrupoValidacao[]>([]);
  readonly carregando = signal(true);
  readonly salvandoTemplate = signal(false);
  readonly salvandoGrupo = signal(false);
  readonly erro = signal('');
  readonly aviso = signal('');
  readonly exibirTemplate = signal(false);
  readonly exibirGrupo = signal(false);

  readonly tiposResposta: Array<{ label: string; value: TipoRespostaChecklist }> = [
    { label: 'Sim / não', value: 'BOOLEAN' },
    { label: 'Texto', value: 'TEXT' },
    { label: 'Número', value: 'NUMBER' },
    { label: 'Data', value: 'DATE' },
    { label: 'Arquivo', value: 'FILE' },
    { label: 'Confirmação', value: 'CONFIRMATION' },
  ];

  readonly versoesTemplatePublicadas = computed(() =>
    this.templates()
      .filter((template) => template.current_version_id !== null)
      .map((template) => ({
        id: template.current_version_id as number,
        label: `${template.code} v${
          template.versions.find(
            (version) => version.id === template.current_version_id,
          )?.version_number ?? ''
        }`,
      })),
  );

  readonly formularioTemplate = this.formBuilder.group({
    code: this.formBuilder.nonNullable.control('', Validators.required),
    name: this.formBuilder.nonNullable.control('', Validators.required),
    description: this.formBuilder.nonNullable.control(''),
    default_due_hours: this.formBuilder.control<number | null>(null),
    items: this.formBuilder.array<PerguntaForm>([this.criarPergunta()]),
  });

  readonly formularioGrupo = this.formBuilder.group({
    code: this.formBuilder.nonNullable.control('', Validators.required),
    name: this.formBuilder.nonNullable.control('', Validators.required),
    description: this.formBuilder.nonNullable.control(''),
    sectors: this.formBuilder.array<RegraForm>([this.criarRegra()]),
  });

  constructor() {
    this.carregar();
  }

  adicionarPergunta(): void {
    this.formularioTemplate.controls.items.push(this.criarPergunta());
  }

  removerPergunta(index: number): void {
    if (this.formularioTemplate.controls.items.length > 1) {
      this.formularioTemplate.controls.items.removeAt(index);
    }
  }

  adicionarRegra(): void {
    this.formularioGrupo.controls.sectors.push(this.criarRegra());
  }

  removerRegra(index: number): void {
    if (this.formularioGrupo.controls.sectors.length > 1) {
      this.formularioGrupo.controls.sectors.removeAt(index);
    }
  }

  criarTemplate(): void {
    if (this.formularioTemplate.invalid || this.salvandoTemplate()) {
      this.formularioTemplate.markAllAsTouched();
      return;
    }
    const value = this.formularioTemplate.getRawValue();
    const payload: NovoTemplate = {
      code: value.code,
      name: value.name,
      description: value.description,
      default_due_hours: value.default_due_hours,
      items: value.items.map((item, index) => ({
        ...item,
        display_order: index + 1,
        config: {},
      })),
    };
    this.salvandoTemplate.set(true);
    this.limparMensagens();
    this.service
      .criarTemplate(payload)
      .pipe(
        finalize(() => this.salvandoTemplate.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () => {
          this.aviso.set('Template criado em rascunho. Publique-o após a revisão.');
          this.exibirTemplate.set(false);
          this.resetarTemplate();
          this.carregar();
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível criar o template.')),
      });
  }

  publicarTemplate(template: TemplateChecklist): void {
    const draft = template.versions.find((version) => version.status === 'DRAFT');
    if (!draft) {
      return;
    }
    this.limparMensagens();
    this.service
      .publicarTemplate(draft.id, template.version)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.aviso.set(`Template ${template.code} publicado.`);
          this.carregar();
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível publicar o template.')),
      });
  }

  criarGrupo(): void {
    if (this.formularioGrupo.invalid || this.salvandoGrupo()) {
      this.formularioGrupo.markAllAsTouched();
      return;
    }
    const value = this.formularioGrupo.getRawValue();
    const payload: NovoGrupo = {
      code: value.code,
      name: value.name,
      description: value.description,
      sectors: value.sectors.map((rule, index) => ({
        sector_id: rule.sector_id as number,
        template_version_id: rule.template_version_id as number,
        is_required: rule.is_required,
        blocks_process: rule.blocks_process,
        due_hours_override: rule.due_hours_override,
        display_order: index + 1,
      })),
    };
    this.salvandoGrupo.set(true);
    this.limparMensagens();
    this.service
      .criarGrupo(payload)
      .pipe(
        finalize(() => this.salvandoGrupo.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () => {
          this.aviso.set('Grupo criado em rascunho. Publique-o após a revisão.');
          this.exibirGrupo.set(false);
          this.resetarGrupo();
          this.carregar();
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível criar o grupo.')),
      });
  }

  publicarGrupo(grupo: GrupoValidacao): void {
    const draft = grupo.versions.find((version) => version.status === 'DRAFT');
    if (!draft) {
      return;
    }
    this.limparMensagens();
    this.service
      .publicarGrupo(draft.id, grupo.version)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.aviso.set(`Grupo ${grupo.code} publicado.`);
          this.carregar();
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível publicar o grupo.')),
      });
  }

  private carregar(): void {
    this.carregando.set(true);
    forkJoin({
      sectors: this.service.listarSetores(),
      templates: this.service.listarTemplates(),
      groups: this.service.listarGrupos(),
    })
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: ({ sectors, templates, groups }) => {
          this.setores.set(sectors.results);
          this.templates.set(templates.results);
          this.grupos.set(groups.results);
        },
        error: (error) =>
          this.erro.set(
            errorMessage(error, 'Não foi possível carregar grupos e templates.'),
          ),
      });
  }

  private criarPergunta(): PerguntaForm {
    return this.formBuilder.group({
      code: this.formBuilder.nonNullable.control('', Validators.required),
      question: this.formBuilder.nonNullable.control('', Validators.required),
      response_type: this.formBuilder.nonNullable.control<TipoRespostaChecklist>(
        'BOOLEAN',
      ),
      is_required: this.formBuilder.nonNullable.control(true),
      blocks_process: this.formBuilder.nonNullable.control(false),
      requires_evidence: this.formBuilder.nonNullable.control(false),
      allows_pending: this.formBuilder.nonNullable.control(true),
    });
  }

  private criarRegra(): RegraForm {
    return this.formBuilder.group({
      sector_id: this.formBuilder.control<number | null>(
        null,
        Validators.required,
      ),
      template_version_id: this.formBuilder.control<number | null>(
        null,
        Validators.required,
      ),
      is_required: this.formBuilder.nonNullable.control(true),
      blocks_process: this.formBuilder.nonNullable.control(true),
      due_hours_override: this.formBuilder.control<number | null>(null),
    });
  }

  private resetarTemplate(): void {
    this.formularioTemplate.reset({
      code: '',
      name: '',
      description: '',
      default_due_hours: null,
    });
    this.formularioTemplate.controls.items.clear();
    this.formularioTemplate.controls.items.push(this.criarPergunta());
  }

  private resetarGrupo(): void {
    this.formularioGrupo.reset({ code: '', name: '', description: '' });
    this.formularioGrupo.controls.sectors.clear();
    this.formularioGrupo.controls.sectors.push(this.criarRegra());
  }

  private limparMensagens(): void {
    this.erro.set('');
    this.aviso.set('');
  }
}
