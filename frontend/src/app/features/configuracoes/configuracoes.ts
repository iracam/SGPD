import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AjudaLink } from '../../core/ajuda/ajuda-link';

@Component({
  selector: 'app-configuracoes-page',
  imports: [RouterLink, AjudaLink],
  templateUrl: './configuracoes.html',
  styleUrl: './configuracoes.scss',
})
export class ConfiguracoesPage {}
