import { Component, inject } from '@angular/core';

import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-painel-page',
  imports: [],
  templateUrl: './painel.html',
  styleUrl: './painel.scss',
})
export class PainelPage {
  protected readonly authService = inject(AuthService);
}
