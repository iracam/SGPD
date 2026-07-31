import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MessageModule } from 'primeng/message';
import { finalize } from 'rxjs';

import { errorMessage } from '../../core/api/api-error';
import { LinhaDuracao, LinhaValor, Relatorios } from './models/relatorios.models';
import { RelatoriosService } from './relatorios.service';

/**
 * Relatórios mínimos do RF-036, somente leitura.
 *
 * O período filtra o fato ocorrido — processo concluído, tarefa concluída,
 * pendência identificada, valor informado, processo aberto ou liberado. Atraso
 * não tem data própria: processo vencido e setor atrasado são a fotografia
 * deste instante, e a tela diz isso em vez de fingir recorte.
 */
@Component({
  selector: 'app-relatorios-page',
  imports: [FormsModule, MessageModule, RouterLink],
  templateUrl: './relatorios.html',
  styleUrl: './relatorios.scss',
})
export class RelatoriosPage {
  private readonly service = inject(RelatoriosService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly relatorios = signal<Relatorios | null>(null);
  protected readonly carregando = signal(true);
  protected readonly erro = signal('');
  protected inicio = '';
  protected fim = '';

  constructor() {
    this.consultar();
  }

  protected consultar(): void {
    this.carregando.set(true);
    this.erro.set('');
    this.service
      .consultar(this.inicio, this.fim)
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (result) => {
          this.relatorios.set(result);
          this.inicio = result.period.start;
          this.fim = result.period.end;
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível carregar os relatórios.')),
      });
  }

  protected horas(linha: LinhaDuracao): string {
    if (linha.average_hours === null) {
      return '—';
    }
    return `${linha.average_hours.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} h`;
  }

  protected dias(valor: number | null): string {
    if (valor === null) {
      return '—';
    }
    return `${valor.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} dias`;
  }

  protected valor(montante: string, moeda: string): string {
    return `${moeda} ${Number(montante).toLocaleString('pt-BR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }

  protected totalMoeda(linha: LinhaValor): string {
    return this.valor(linha.informed, linha.currency);
  }
}
