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
import { DialogModule } from 'primeng/dialog';
import { InputNumberModule } from 'primeng/inputnumber';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { SelectModule } from 'primeng/select';
import { TextareaModule } from 'primeng/textarea';
import { finalize, forkJoin } from 'rxjs';

import { AjudaLink } from '../../core/ajuda/ajuda-link';
import { errorMessage } from '../../core/api/api-error';
import {
  AtualizacaoRascunhoGrupo,
  AtualizacaoRascunhoTemplate,
  GrupoValidacao,
  ItemTemplate,
  NovaRegraAplicabilidade,
  NovoGrupo,
  NovoTemplate,
  NovaVersaoGrupo,
  NovaVersaoTemplate,
  RegraAplicabilidade,
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
    DialogModule,
    InputNumberModule,
    InputTextModule,
    MessageModule,
    SelectModule,
    TextareaModule,
    AjudaLink,
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
  readonly regrasAplicabilidade = signal<RegraAplicabilidade[]>([]);
  readonly carregando = signal(true);
  readonly salvandoTemplate = signal(false);
  readonly salvandoGrupo = signal(false);
  readonly salvandoRegra = signal(false);
  readonly erro = signal('');
  readonly aviso = signal('');
  readonly exibirTemplate = signal(false);
  readonly exibirGrupo = signal(false);
  readonly exibirRegra = signal(false);
  readonly templateEmEdicao = signal<TemplateChecklist | null>(null);
  readonly grupoEmEdicao = signal<GrupoValidacao | null>(null);
  readonly regraEmEdicao = signal<RegraAplicabilidade | null>(null);
  readonly previewTemplate = signal(false);
  readonly previewGrupo = signal(false);

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

  readonly gruposPublicados = computed(() =>
    this.grupos()
      .filter((grupo) => grupo.is_active && grupo.current_version_id !== null)
      .map((grupo) => ({ id: grupo.id, label: `#${grupo.code} · ${grupo.name}` })),
  );

  readonly formularioRegra = this.formBuilder.group({
    name: this.formBuilder.nonNullable.control('', Validators.required),
    priority: this.formBuilder.nonNullable.control(100, Validators.required),
    group_id: this.formBuilder.control<number | null>(null, Validators.required),
    company_code: this.formBuilder.control<number | null>(null),
    branch_code: this.formBuilder.control<number | null>(null),
    employee_type_code: this.formBuilder.control<number | null>(null),
    job_structure_code: this.formBuilder.control<number | null>(null),
    job_code: this.formBuilder.nonNullable.control(''),
    cost_center_code: this.formBuilder.nonNullable.control(''),
    is_active: this.formBuilder.nonNullable.control(true),
    valid_from: this.formBuilder.nonNullable.control(''),
    valid_to: this.formBuilder.nonNullable.control(''),
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

  abrirPreviewTemplate(): void {
    this.previewTemplate.set(true);
  }

  fecharPreviewTemplate(): void {
    this.previewTemplate.set(false);
  }

  // Enum cru nunca chega ao usuário (ADR-047).
  rotuloVersao(status: 'DRAFT' | 'PUBLISHED' | 'RETIRED'): string {
    return status === 'PUBLISHED'
      ? 'Publicada'
      : status === 'DRAFT'
        ? 'Rascunho'
        : 'Retirada';
  }

  estadoVersao(status: 'DRAFT' | 'PUBLISHED' | 'RETIRED'): string {
    return status === 'PUBLISHED' ? 'released' : status === 'DRAFT' ? 'pending' : 'canceled';
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

  abrirPreviewGrupo(): void {
    this.previewGrupo.set(true);
  }

  fecharPreviewGrupo(): void {
    this.previewGrupo.set(false);
  }

  rotuloSetor(id: number | null): string {
    return this.setores().find((setor) => setor.id === id)?.name ?? '—';
  }

  versaoTemplateResolvida(
    id: number | null,
  ): { template: TemplateChecklist; versao: VersaoTemplate } | null {
    if (id === null) {
      return null;
    }
    for (const template of this.templates()) {
      const versao = template.versions.find((item) => item.id === id);
      if (versao) {
        return { template, versao };
      }
    }
    return null;
  }

  // Mesma precedência do backend: override do grupo > SLA do template > SLA do setor.
  slaEfetivoRegra(regra: RegraForm): number | null {
    const override = regra.controls.due_hours_override.value;
    if (override) {
      return override;
    }
    const resolvida = this.versaoTemplateResolvida(regra.controls.template_version_id.value);
    if (resolvida?.versao.default_due_hours) {
      return resolvida.versao.default_due_hours;
    }
    const setor = this.setores().find((item) => item.id === regra.controls.sector_id.value);
    return setor?.default_due_hours ?? null;
  }

  opcoesEscolha(item: ItemTemplate): string[] {
    const choices = item.config['choices'];
    return Array.isArray(choices)
      ? choices.filter((opcao): opcao is string => typeof opcao === 'string')
      : [];
  }

  notasConfiguracao(blocksProcess: boolean, allowsPending: boolean): string {
    const notas: string[] = [];
    if (blocksProcess) {
      notas.push('Bloqueia a conclusão do processo');
    }
    if (allowsPending) {
      notas.push('Permite registrar pendência');
    }
    return notas.join(' · ');
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

  excluirRascunhoTemplate(template: TemplateChecklist): void {
    const draft = this.rascunhoTemplate(template);
    if (!draft || this.salvandoTemplate()) {
      return;
    }
    if (!confirm(`Excluir o rascunho v${draft.version_number} do template #${template.code}?`)) {
      return;
    }
    this.salvandoTemplate.set(true);
    this.limparMensagens();
    this.service
      .excluirRascunhoTemplate(draft.id, template.version)
      .pipe(
        finalize(() => this.salvandoTemplate.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () => {
          this.aviso.set(
            `Rascunho v${draft.version_number} do template #${template.code} excluído.`,
          );
          this.carregar();
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível excluir o rascunho.')),
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

  criarNovaVersaoGrupo(grupo: GrupoValidacao): void {
    if (this.rascunhoGrupo(grupo) || this.salvandoGrupo()) {
      return;
    }
    const published = grupo.versions.find(
      (version) => version.id === grupo.current_version_id,
    );
    if (!published) {
      return;
    }
    const payload: NovaVersaoGrupo = {
      expected_version: grupo.version,
      sectors: published.sectors.map((regra, index) => ({
        sector_id: regra.sector.id,
        template_version_id:
          this.templates().find(
            (template) => template.id === regra.template_version.template_id,
          )?.current_version_id ?? regra.template_version.id,
        is_required: regra.is_required,
        blocks_process: regra.blocks_process,
        due_hours_override: regra.due_hours_override,
        display_order: index + 1,
      })),
    };
    this.salvandoGrupo.set(true);
    this.limparMensagens();
    this.service
      .criarVersaoGrupo(grupo.id, payload)
      .pipe(
        finalize(() => this.salvandoGrupo.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (draft) => {
          const atualizado: GrupoValidacao = {
            ...grupo,
            version: grupo.version + 1,
            versions: [draft, ...grupo.versions],
          };
          this.grupos.update((grupos) =>
            grupos.map((item) => (item.id === grupo.id ? atualizado : item)),
          );
          this.editarRascunhoGrupo(atualizado);
          this.aviso.set(
            `Versão ${draft.version_number} do grupo #${grupo.code} criada em rascunho.`,
          );
        },
        error: (error) =>
          this.erro.set(
            errorMessage(error, 'Não foi possível criar uma nova versão do grupo.'),
          ),
      });
  }

  excluirRascunhoGrupo(grupo: GrupoValidacao): void {
    const draft = this.rascunhoGrupo(grupo);
    if (!draft || this.salvandoGrupo()) {
      return;
    }
    if (!confirm(`Excluir o rascunho v${draft.version_number} do grupo #${grupo.code}?`)) {
      return;
    }
    this.salvandoGrupo.set(true);
    this.limparMensagens();
    this.service
      .excluirRascunhoGrupo(draft.id, grupo.version)
      .pipe(
        finalize(() => this.salvandoGrupo.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () => {
          this.aviso.set(`Rascunho v${draft.version_number} do grupo #${grupo.code} excluído.`);
          this.carregar();
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível excluir o rascunho.')),
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

  abrirNovaRegraAplicabilidade(): void {
    this.regraEmEdicao.set(null);
    this.resetarRegraAplicabilidade();
    this.exibirRegra.set(true);
    this.limparMensagens();
  }

  editarRegraAplicabilidade(regra: RegraAplicabilidade): void {
    this.regraEmEdicao.set(regra);
    this.formularioRegra.reset({
      name: regra.name,
      priority: regra.priority,
      group_id: regra.group.id,
      company_code: regra.company_code,
      branch_code: regra.branch_code,
      employee_type_code: regra.employee_type_code,
      job_structure_code: regra.job_structure_code,
      job_code: regra.job_code ?? '',
      cost_center_code: regra.cost_center_code ?? '',
      is_active: regra.is_active,
      valid_from: regra.valid_from ?? '',
      valid_to: regra.valid_to ?? '',
    });
    this.exibirRegra.set(true);
    this.limparMensagens();
  }

  cancelarEditorRegraAplicabilidade(): void {
    this.exibirRegra.set(false);
    this.regraEmEdicao.set(null);
    this.resetarRegraAplicabilidade();
  }

  salvarRegraAplicabilidade(): void {
    if (this.formularioRegra.invalid || this.salvandoRegra()) {
      this.formularioRegra.markAllAsTouched();
      return;
    }
    const value = this.formularioRegra.getRawValue();
    const payload: NovaRegraAplicabilidade = {
      name: value.name,
      priority: value.priority,
      group_id: value.group_id as number,
      company_code: value.company_code,
      branch_code: value.branch_code,
      employee_type_code: value.employee_type_code,
      job_structure_code: value.job_structure_code,
      job_code: value.job_code.trim() || null,
      cost_center_code: value.cost_center_code.trim() || null,
      is_active: value.is_active,
      valid_from: value.valid_from || null,
      valid_to: value.valid_to || null,
    };
    const regra = this.regraEmEdicao();
    const request = regra
      ? this.service.atualizarRegraAplicabilidade(regra.id, {
          ...payload,
          expected_version: regra.version,
        })
      : this.service.criarRegraAplicabilidade(payload);
    this.salvandoRegra.set(true);
    this.limparMensagens();
    request
      .pipe(
        finalize(() => this.salvandoRegra.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (salva) => {
          this.aviso.set(
            regra
              ? `Regra "${salva.name}" atualizada.`
              : `Regra "${salva.name}" criada.`,
          );
          this.exibirRegra.set(false);
          this.regraEmEdicao.set(null);
          this.resetarRegraAplicabilidade();
          this.carregar();
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível salvar a regra.')),
      });
  }

  descricaoFiltroRegra(regra: RegraAplicabilidade): string {
    const filtros = [
      ['Empresa', regra.company_code],
      ['Filial', regra.branch_code],
      ['Tipo', regra.employee_type_code],
      ['Estrutura', regra.job_structure_code],
      ['Cargo', regra.job_code],
      ['Centro de custo', regra.cost_center_code],
    ]
      .filter(([, valor]) => valor !== null && valor !== '')
      .map(([rotulo, valor]) => `${rotulo} ${valor}`);
    return filtros.length > 0 ? filtros.join(' · ') : 'Sem filtro — sugere sempre';
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
      rules: this.service.listarRegrasAplicabilidade(),
    })
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: ({ sectors, templates, groups, rules }) => {
          this.setores.set(sectors.results);
          this.templates.set(templates.results);
          this.grupos.set(groups.results);
          this.regrasAplicabilidade.set(rules.results);
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

  private resetarRegraAplicabilidade(): void {
    this.formularioRegra.reset({
      name: '',
      priority: 100,
      group_id: null,
      company_code: null,
      branch_code: null,
      employee_type_code: null,
      job_structure_code: null,
      job_code: '',
      cost_center_code: '',
      is_active: true,
      valid_from: '',
      valid_to: '',
    });
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
