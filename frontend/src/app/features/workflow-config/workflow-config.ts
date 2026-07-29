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
  AtualizacaoRascunhoGrupo,
  AtualizacaoRascunhoTemplate,
  GrupoValidacao,
  ItemTemplate,
  NovoGrupo,
  NovoTemplate,
  NovaVersaoTemplate,
  RegraGrupo,
  SetorWorkflow,
  TemplateChecklist,
  TipoRespostaChecklist,
  VersaoGrupo,
  VersaoTemplate,
} from './models/workflow-config.models';
import { WorkflowConfigService } from './workflow-config.service';

type PerguntaForm = FormGroup<{
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
  readonly templatesVisiveis = signal<TemplateChecklist[]>([]);
  readonly grupos = signal<GrupoValidacao[]>([]);
  readonly carregando = signal(true);
  readonly salvandoTemplate = signal(false);
  readonly salvandoGrupo = signal(false);
  readonly erro = signal('');
  readonly aviso = signal('');
  readonly exibirTemplate = signal(false);
  readonly exibirGrupo = signal(false);
  readonly buscaTemplate = signal('');
  readonly templateEmEdicao = signal<TemplateChecklist | null>(null);
  readonly grupoEmEdicao = signal<GrupoValidacao | null>(null);

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
        label: `#${template.code} · ${template.name} · v${
          template.versions.find(
            (version) => version.id === template.current_version_id,
          )?.version_number ?? ''
        }`,
      })),
  );

  readonly formularioTemplate = this.formBuilder.group({
    name: this.formBuilder.nonNullable.control('', Validators.required),
    description: this.formBuilder.nonNullable.control(''),
    default_due_hours: this.formBuilder.control<number | null>(null),
    items: this.formBuilder.array<PerguntaForm>([this.criarPergunta()]),
  });

  readonly formularioGrupo = this.formBuilder.group({
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

  abrirNovoTemplate(): void {
    this.templateEmEdicao.set(null);
    this.resetarTemplate();
    this.exibirTemplate.set(true);
    this.limparMensagens();
  }

  editarRascunho(template: TemplateChecklist): void {
    const draft = this.rascunhoTemplate(template);
    if (!draft) {
      return;
    }
    this.templateEmEdicao.set(template);
    this.formularioTemplate.reset({
      name: template.name,
      description: template.description,
      default_due_hours: draft.default_due_hours,
    });
    this.formularioTemplate.controls.items.clear();
    for (const pergunta of draft.items) {
      this.formularioTemplate.controls.items.push(this.criarPergunta(pergunta));
    }
    this.exibirTemplate.set(true);
    this.limparMensagens();
  }

  cancelarEditorTemplate(): void {
    this.exibirTemplate.set(false);
    this.templateEmEdicao.set(null);
    this.resetarTemplate();
  }

  abrirNovoGrupo(): void {
    this.grupoEmEdicao.set(null);
    this.resetarGrupo();
    this.exibirGrupo.set(true);
    this.limparMensagens();
  }

  editarRascunhoGrupo(grupo: GrupoValidacao): void {
    const draft = this.rascunhoGrupo(grupo);
    if (!draft) {
      return;
    }
    this.grupoEmEdicao.set(grupo);
    this.formularioGrupo.reset({
      name: grupo.name,
      description: grupo.description,
    });
    this.formularioGrupo.controls.sectors.clear();
    for (const regra of draft.sectors) {
      this.formularioGrupo.controls.sectors.push(this.criarRegra(regra));
    }
    this.exibirGrupo.set(true);
    this.limparMensagens();
  }

  cancelarEditorGrupo(): void {
    this.exibirGrupo.set(false);
    this.grupoEmEdicao.set(null);
    this.resetarGrupo();
  }

  salvarTemplate(): void {
    if (this.formularioTemplate.invalid || this.salvandoTemplate()) {
      this.formularioTemplate.markAllAsTouched();
      return;
    }
    const value = this.formularioTemplate.getRawValue();
    const payload: NovoTemplate = {
      name: value.name,
      description: value.description,
      default_due_hours: value.default_due_hours,
      items: value.items.map((item, index) => ({
        ...item,
        display_order: index + 1,
        config: {},
      })),
    };
    const template = this.templateEmEdicao();
    const draft = template ? this.rascunhoTemplate(template) : undefined;
    const request =
      template && draft
        ? this.service.atualizarRascunhoTemplate(draft.id, {
            ...payload,
            expected_version: template.version,
          } satisfies AtualizacaoRascunhoTemplate)
        : this.service.criarTemplate(payload);
    this.salvandoTemplate.set(true);
    this.limparMensagens();
    request
      .pipe(
        finalize(() => this.salvandoTemplate.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (savedTemplate) => {
          this.aviso.set(
            template
              ? `Rascunho do template #${savedTemplate.code} atualizado.`
              : `Template #${savedTemplate.code} criado em rascunho.`,
          );
          this.exibirTemplate.set(false);
          this.templateEmEdicao.set(null);
          this.buscaTemplate.set('');
          this.resetarTemplate();
          this.carregar();
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível criar o template.')),
      });
  }

  criarNovaVersao(template: TemplateChecklist): void {
    if (this.rascunhoTemplate(template) || this.salvandoTemplate()) {
      return;
    }
    const published = template.versions.find(
      (version) => version.id === template.current_version_id,
    );
    if (!published) {
      return;
    }
    const payload: NovaVersaoTemplate = {
      expected_version: template.version,
      default_due_hours: published.default_due_hours,
      items: this.itensParaPayload(published.items),
    };
    this.salvandoTemplate.set(true);
    this.limparMensagens();
    this.service
      .criarVersaoTemplate(template.id, payload)
      .pipe(
        finalize(() => this.salvandoTemplate.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (draft) => {
          const atualizado: TemplateChecklist = {
            ...template,
            version: template.version + 1,
            versions: [draft, ...template.versions],
          };
          this.templates.update((templates) =>
            templates.map((item) => (item.id === template.id ? atualizado : item)),
          );
          this.templatesVisiveis.update((templates) =>
            templates.map((item) => (item.id === template.id ? atualizado : item)),
          );
          this.editarRascunho(atualizado);
          this.aviso.set(
            `Versão ${draft.version_number} do template #${template.code} criada em rascunho.`,
          );
        },
        error: (error) =>
          this.erro.set(
            errorMessage(error, 'Não foi possível criar uma nova versão do template.'),
          ),
      });
  }

  publicarTemplate(template: TemplateChecklist): void {
    const draft = this.rascunhoTemplate(template);
    if (!draft) {
      return;
    }
    this.limparMensagens();
    this.service
      .publicarTemplate(draft.id, template.version)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.aviso.set(`Template #${template.code} publicado.`);
          this.buscaTemplate.set('');
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
    const grupo = this.grupoEmEdicao();
    const draft = grupo ? this.rascunhoGrupo(grupo) : undefined;
    const request =
      grupo && draft
        ? this.service.atualizarRascunhoGrupo(draft.id, {
            ...payload,
            expected_version: grupo.version,
          } satisfies AtualizacaoRascunhoGrupo)
        : this.service.criarGrupo(payload);
    this.salvandoGrupo.set(true);
    this.limparMensagens();
    request
      .pipe(
        finalize(() => this.salvandoGrupo.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (savedGroup) => {
          this.aviso.set(
            grupo
              ? `Rascunho do grupo #${savedGroup.code} atualizado.`
              : `Grupo #${savedGroup.code} criado em rascunho.`,
          );
          this.exibirGrupo.set(false);
          this.grupoEmEdicao.set(null);
          this.resetarGrupo();
          this.carregar();
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível salvar o grupo.')),
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
          this.aviso.set(`Grupo #${grupo.code} publicado.`);
          this.carregar();
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível publicar o grupo.')),
      });
  }

  buscarTemplates(): void {
    this.carregando.set(true);
    this.limparMensagens();
    this.service
      .listarTemplates(this.buscaTemplate())
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (templates) => this.templatesVisiveis.set(templates.results),
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível buscar os templates.')),
      });
  }

  rascunhoTemplate(template: TemplateChecklist): VersaoTemplate | undefined {
    return template.versions.find((version) => version.status === 'DRAFT');
  }

  rascunhoGrupo(grupo: GrupoValidacao): VersaoGrupo | undefined {
    return grupo.versions.find((version) => version.status === 'DRAFT');
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
          this.templatesVisiveis.set(templates.results);
          this.grupos.set(groups.results);
        },
        error: (error) =>
          this.erro.set(
            errorMessage(error, 'Não foi possível carregar grupos e templates.'),
          ),
      });
  }

  private criarPergunta(item?: ItemTemplate): PerguntaForm {
    return this.formBuilder.group({
      question: this.formBuilder.nonNullable.control(
        item?.question ?? '',
        Validators.required,
      ),
      response_type: this.formBuilder.nonNullable.control<TipoRespostaChecklist>(
        item?.response_type ?? 'BOOLEAN',
      ),
      is_required: this.formBuilder.nonNullable.control(item?.is_required ?? true),
      blocks_process: this.formBuilder.nonNullable.control(item?.blocks_process ?? false),
      requires_evidence: this.formBuilder.nonNullable.control(
        item?.requires_evidence ?? false,
      ),
      allows_pending: this.formBuilder.nonNullable.control(item?.allows_pending ?? true),
    });
  }

  private criarRegra(regra?: RegraGrupo): RegraForm {
    return this.formBuilder.group({
      sector_id: this.formBuilder.control<number | null>(
        regra?.sector.id ?? null,
        Validators.required,
      ),
      template_version_id: this.formBuilder.control<number | null>(
        regra?.template_version.id ?? null,
        Validators.required,
      ),
      is_required: this.formBuilder.nonNullable.control(regra?.is_required ?? true),
      blocks_process: this.formBuilder.nonNullable.control(
        regra?.blocks_process ?? true,
      ),
      due_hours_override: this.formBuilder.control<number | null>(
        regra?.due_hours_override ?? null,
      ),
    });
  }

  private resetarTemplate(): void {
    this.formularioTemplate.reset({
      name: '',
      description: '',
      default_due_hours: null,
    });
    this.formularioTemplate.controls.items.clear();
    this.formularioTemplate.controls.items.push(this.criarPergunta());
  }

  private itensParaPayload(
    items: ItemTemplate[],
  ): Array<Omit<ItemTemplate, 'id' | 'code'>> {
    return items.map(({ id: _id, code: _code, ...item }) => item);
  }

  private resetarGrupo(): void {
    this.formularioGrupo.reset({ name: '', description: '' });
    this.formularioGrupo.controls.sectors.clear();
    this.formularioGrupo.controls.sectors.push(this.criarRegra());
  }

  private limparMensagens(): void {
    this.erro.set('');
    this.aviso.set('');
  }
}
