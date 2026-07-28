import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { PasswordModule } from 'primeng/password';
import { finalize } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { ApiError } from '../../core/auth/models/auth.models';

@Component({
  selector: 'app-senha-page',
  imports: [ReactiveFormsModule, ButtonModule, MessageModule, PasswordModule],
  templateUrl: './senha.html',
  styleUrl: './senha.scss',
})
export class SenhaPage {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly mustChange = this.authService.mustChangePassword;
  readonly isSubmitting = signal(false);
  readonly errorMessage = signal('');
  /** Erros por campo vindos de `details` do envelope da API. */
  readonly fieldErrors = signal<Record<string, string[]>>({});

  readonly form = this.formBuilder.nonNullable.group({
    old_password: ['', [Validators.required]],
    new_password: ['', [Validators.required]],
    new_password_confirm: ['', [Validators.required]],
  });

  errorsFor(field: string): string[] {
    return this.fieldErrors()[field] ?? [];
  }

  submit(): void {
    if (this.form.invalid || this.isSubmitting()) {
      this.form.markAllAsTouched();
      return;
    }

    this.errorMessage.set('');
    this.fieldErrors.set({});
    this.isSubmitting.set(true);

    this.authService
      .changePassword(this.form.getRawValue())
      .pipe(
        finalize(() => this.isSubmitting.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () => void this.router.navigateByUrl('/fe/painel'),
        error: (error: HttpErrorResponse) => this.applyApiError(error),
      });
  }

  private applyApiError(error: HttpErrorResponse): void {
    const body = error.error as ApiError | null;
    const details = body?.details ?? {};
    const normalized: Record<string, string[]> = {};
    for (const [field, messages] of Object.entries(details)) {
      normalized[field] = Array.isArray(messages) ? messages : [messages];
    }
    this.fieldErrors.set(normalized);
    this.errorMessage.set(
      normalized['non_field_errors']?.join(' ') ??
        body?.message ??
        'Não foi possível alterar a senha.',
    );
  }
}
