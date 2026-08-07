import { HttpErrorResponse } from '@angular/common/http';
import {
  Component,
  DestroyRef,
  ElementRef,
  afterNextRender,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { PasswordModule } from 'primeng/password';
import { finalize } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { ApiError } from '../../core/auth/models/auth.models';

@Component({
  selector: 'app-login-page',
  imports: [ReactiveFormsModule, ButtonModule, InputTextModule, MessageModule, PasswordModule],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class LoginPage {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly isSubmitting = signal(false);
  readonly errorMessage = signal('');

  readonly form = this.formBuilder.nonNullable.group({
    username: ['', [Validators.required]],
    password: ['', [Validators.required]],
  });

  private readonly usernameInput = viewChild.required<ElementRef<HTMLInputElement>>('usernameInput');

  constructor() {
    afterNextRender(() => this.usernameInput().nativeElement.focus());
  }

  submit(): void {
    if (this.form.invalid || this.isSubmitting()) {
      this.form.markAllAsTouched();
      return;
    }

    this.errorMessage.set('');
    this.isSubmitting.set(true);

    this.authService
      .login(this.form.getRawValue())
      .pipe(
        finalize(() => this.isSubmitting.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (user) => {
          const target = user.must_change_password ? '/fe/senha' : '/fe/painel';
          void this.router.navigateByUrl(target);
        },
        error: (error: HttpErrorResponse) => {
          const body = error.error as ApiError | null;
          this.errorMessage.set(body?.message ?? 'Não foi possível autenticar.');
        },
      });
  }
}
